from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import PumpCharacteristic
from .serializers_pump import PumpCharacteristicSerializer, PumpCharacteristicListSerializer


class PumpCharacteristicViewSet(viewsets.ModelViewSet):
    """
    ViewSet для обработки операций CRUD с характеристиками насосов ЭЦН.

    Предоставляет полный REST API для работы с насосами:
    - просмотр списка и деталей насоса;
    - фильтрация и поиск;
    - построение графиков характеристик;
    - подбор насосов по параметрам.
    """
    queryset = PumpCharacteristic.objects.filter(is_active=True)
    serializer_class = PumpCharacteristicSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Поиск. Пример запроса: GET/api/pumps/?search=ТД175 - будет искать "ТД175" в обоих полях
    search_fields = [
        'harka_stupen',
        'zavod'
    ]

    # Список полей, по которым разрешена сортировка
    # Примеры запросов:
    # ?ordering=nominal_range
    # ?ordering=-max_efficiency
    # ?ordering=stages_count,-nominal_head
    ordering_fields = [
        'cod',
        'nominal_range',
        'nominal_head',
        'max_efficiency',
        'stages_count',
    ]
    # Поле сортировки по умолчанию
    ordering = ['nominal_range']

    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        self.action - автоматическое свойство DRF, которое содержит
        текущее действие (list, retrieve, create и т.д.)

        Returns:
            Serializer: Выбранный сериализатор
        """
        if self.action == 'list':
            return PumpCharacteristicListSerializer
        return PumpCharacteristicSerializer

    def get_queryset(self):
        """
        Фильтрация QuerySet по параметрам запроса.
        Цель: добавить фильтрацию по диапазонам значений (подача, напор, КПД),
        которая не поддерживается filterset_fields

        Returns:
            QuerySet: Отфильтрованный набор насосов
        """
        queryset = super().get_queryset()

        # Фильтрация по номинальной подаче
        # Пример: ?min_flow=100&max_flow=300
        min_flow = self.request.query_params.get('min_flow')
        max_flow = self.request.query_params.get('max_flow')

        if min_flow:
            queryset = queryset.filter(nominal_range__gte=float(min_flow))
        if max_flow:
            queryset = queryset.filter(nominal_range__lte=float(max_flow))

        # Фильтрация по напору
        min_head = self.request.query_params.get('min_head')
        max_head = self.request.query_params.get('max_head')

        if min_head:
            queryset = queryset.filter(nominal_head__gte=float(min_head))
        if max_head:
            queryset = queryset.filter(nominal_head__lte=float(max_head))

        # Фильтрация по КПД
        min_efficiency = self.request.query_params.get('min_efficiency')
        if min_efficiency:
            queryset = queryset.filter(max_efficiency__gte=float(min_efficiency))

        return queryset

    @action(detail=True, methods=['ger'])
    def characteristics(self, request, pk=None):
        """
        Получение полных характеристик насоса для построения графиков.

        Args:
            request: HTTP запрос
            pk: ID насоса

        Returns:
            Response: Данные характеристик
        """
        pump = self.get_object()

        characteristics_data = {
            'pump_info': {
                'id': pump.id,
                'name': pump.harka_stupen,
                'manufacturer': pump.zavod,
                'nominal_flow': pump.nomnal_range,
                'nominal_head': pump.nominal_head,
                'stages': pump.stages_count,
            },
            'characteristics': {
                'q_values': pump.q_values,
                'h_values': pump.h_values,
                'n_values': pump.n_values,
                'kpd_values': pump.kpd_values,
            },
            'ranges': {
                'working': [pump.left_range, pump.right_range],
                'optimal': pump.optimal_flow_range if pump.optimal_flow_range else [],
                'nominal': pump.nominal_range,
            },
            'efficiency': {
                'max': pump.max_efficiency,
                'max_flow': pump.max_efficiency_flow,
                'threshold_75_percent': pump.max_efficiency * 0.75 if pump.efficiency else None,
            }
        }

        return Response(characteristics_data)

    @action(detail=True, methods=['get'])
    def calculate_point(self, request, pk=None):
        """
        Расчет параметров насоса в заданной точке.
        URL: GET /api/pumps/{id}/calculate_point/?flow=150&density=850

        Параметры запроса:
        - flow: подача, м³/сут (обязательный)
        - density: плотность жидкости, кг/м³ (по умолчанию 850)

        Args:
            request: HTTP запрос
            pk: ID насоса

        Returns:
            Response: расчетные параметры
        """
        pump = self.get_object()

        flow = self.request.query_params.get('flow')
        if not flow:
            return Response(
                {'error': 'Параметр "flow" обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flow_value = float(flow)
            density = float(request.query_params.get('density, 850.0'))

            # Используем метод модели для расчета
            result = pump.calculate_at_point(flow_value)
            power_data = pump.calculate_power_consumption(flow_value, density)

            # Формирование ответа с расчетами
            # Пример URL: GET /api/pumps/{5}/calculate_point/?flow=150&density=870
            response_data = {
                'input': {
                    'flow': flow_value,
                    'density': density,
                },
                'characteristics': result,
                'power_calculation': power_data,
                'recommendation': self._get_recommendation(result, pump)
            }

            return Response(response_data)

        except ValueError as e:
            return Response(
                {'error': f'Неверный формат параметров: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def find_suitable(self, request):
        """
        Подбор насосов по требуемым параметрам.

        Параметры запросы:
        - required_flow: требуемая подача, м³/сут (обязательный)
        - required_head: требуемый напор, м (обязательный)
        - tolerance: допуск, % (по умолчанию 10)
        - min_efficiency: минимальный КПД, % (по умолчанию 25)

        Agrs:
            request: HTTP запрос
            URL: GET api/pumps/find_suitable/?required_flow=150&required_head=1000

        Returns:
            Response: список подходящих насосов
        """
        required_flow = self.request.query_params.get('required_flow')
        required_head = self.request.query_params.get('required_head')

        if not required_flow or not required_head:
            return Response(
                {'error': 'Параметры "required_flow" и "required_head" обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flow = float(required_flow)
            head = float(required_head)
            tolerance = float(request.query_params.get('tolerance', 10.0)) / 100
            min_efficiency = float(request.query_params.get('min_efficiency', 25.0))

            suitable_pumps = []

            for pump in self.get_queryset():
                # Проверяем, что насос может обеспечить требуемые параметры
                if (pump.left_range <= flow <= pump.right_range and pump.nominal_head and
                        abs(pump.niminal_head - head) / head <= tolerance):
                    # Рассчитываем КПД в этой точке
                    point_data = pump.calculate_at_point(flow)

                    if point_data['kpd'] >= min_efficiency:
                        pump_data = PumpCharacteristicListSerializer(pump).data
                        pump_data['calculated_efficiency'] = point_data['kpd']
                        pump_data['calculated_head'] = point_data['h']
                        pump_data['calculated_power'] = point_data['n']
                        pump_data['is_in_optimal_range'] = point_data['is_optimal']

                        suitable_pumps.append(pump_data)

            suitable_pumps.sort(key=lambda x: x['calculated_efficiency'], reverse=True)

            return Response({
                'search_parameters': {
                    'required_flow': flow,
                    'required_head': head,
                    'tolerance_percent': tolerance * 100,
                    'min_efficiency': min_efficiency,
                },
                'found_count': len(suitable_pumps),
                'pumps': suitable_pumps[:10],  # Ограничиваем 10 лучшими
            })

        except ValueError as e:
            return Response(
                {'error': f'Неверный формат параметров: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Статистика по всем насосам.

        Args:
            request: HTTP запрос

        Returns:
            Response: статистические данные
        """
