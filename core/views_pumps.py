from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import PumpCharacteristic
from .serializers_pump import PumpCharacteristicSerializer, PumpCharacteristicListSerializer
from django.db import models


class PumpCharacteristicViewSet(viewsets.ModelViewSet):
    """
    ViewSet для обработки операций CRUD с характеристиками насосов ЭЦН.
    """
    queryset = PumpCharacteristic.objects.filter(is_active=True)
    serializer_class = PumpCharacteristicSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # DjangoFilterBackend — фильтрация по полям (?field=value)
    # filters.SearchFilter — полнотекстовый поиск (?search=query)
    # filters.OrderingFilter — сортировка (?ordering=field)

    filterset_fields = [        # ?zavod=ESP          ← ТОЧНО
        'zavod',
        'material_stupen',
        'stages_count',
    ]

    search_fields = [           # ?search=ТД          ← СОДЕРЖИТ
        'harka_stupen',
        'zavod'
    ]

    ordering_fields = [         # ?ordering=-cod      ← СОРТИРОВКА
        'cod',
        'nominal_range',
        'nominal_head',
        'max_efficiency',
        'stages_count',
    ]
    ordering = ['nominal_range']    # сортировка по умолчанию

    # Один запрос может всё:
    # GET /api/pumps/?zavod=ESP&search=ТД&ordering=-max_efficiency

    # 1. Только ESP (фильтр)
    # 2. Содержит "ТД" (поиск)
    # 3. Отсортировано по КПД (сортировка)

    def get_serializer_class(self):
        if self.action == 'list':
            return PumpCharacteristicListSerializer
        return self.serializer_class

    # get_serializer_class() вызывается при ЛЮБОМ запросе к API:
    # GET /api/pumps/  # → get_serializer_class() → выбирает сериализатор
    # POST /api/pumps/  # → get_serializer_class() → выбирает сериализатор
    # GET /api/pumps/1/  # → get_serializer_class() → выбирает сериализатор
    # GET /api/pumps/1/characteristics/  # → get_serializer_class() → выбирает сериализатор
    # self.action — встроенный атрибут DRF, это название текущего действия в ViewSet
    # Автоматически заполняется Django REST Framework для каждого запроса.
    # Примеры:
    # GET /api/pumps/ → self.action = 'list'
    # GET /api/pumps/1/ → self.action = 'retrieve'
    # POST /api/pumps/ → self.action = 'create'
    # GET /api/pumps/1/characteristics/ → self.action = 'characteristics'

    def get_queryset(self):
        """
        Когда вызывается: ПЕРЕД ЛЮБЫМ обращением к данным в ViewSet.
        Как: Автоматически DRF.
        Зачем: Получить/отфильтровать данные перед операцией.

        Вызывается при:
        GET /api/pumps/ → get_queryset() → список
        GET /api/pumps/1/ → get_queryset() → детали
        GET /api/pumps/find_suitable/ → get_queryset() → подбор
        PUT /api/pumps/1/ → get_queryset() → поиск объекта
        """
        queryset = super().get_queryset()  # получить БАЗОВЫЙ queryset перед модификацией

        min_flow = self.request.query_params.get('min_flow')
        max_flow = self.request.query_params.get('max_flow')

        if min_flow:
            queryset = queryset.filter(nominal_range__gte=float(min_flow))
        if max_flow:
            queryset = queryset.filter(nominal_range__lte=float(max_flow))

        min_head = self.request.query_params.get('min_head')
        max_head = self.request.query_params.get('max_head')

        if min_head:
            queryset = queryset.filter(nominal_head__gte=float(min_head))
        if max_head:
            queryset = queryset.filter(nominal_head__lte=float(max_head))

        min_efficiency = self.request.query_params.get('min_efficiency')
        if min_efficiency:
            queryset = queryset.filter(max_efficiency__gte=float(min_efficiency))

        return queryset

    @action(detail=True, methods=['get'])
    def characteristics(self, request, pk=None):
        """
        Получение полных характеристик насоса для построения графиков.
        """
        pump = self.get_object()

        characteristics_data = {
            'pump_info': {
                'id': pump.id,
                'name': pump.harka_stupen,
                'manufacturer': pump.zavod,
                'nominal_flow': pump.nominal_range,
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
                'threshold_75_percent': pump.max_efficiency * 0.75 if pump.max_efficiency else None,  # ИСПРАВЛЕНО
            }
        }

        return Response(characteristics_data)

    @action(detail=True, methods=['get'])
    def calculate_point(self, request, pk=None):
        """
        Расчет параметров насоса в заданной точке.
        """
        pump = self.get_object()

        flow = request.query_params.get('flow')  # ИСПРАВЛЕНО: self.request -> request
        if not flow:
            return Response(
                {'error': 'Параметр "flow" обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flow_value = float(flow)
            density = float(request.query_params.get('density', 850.0))  # ИСПРАВЛЕНО: убрана лишняя кавычка

            result = pump.calculate_at_point(flow_value)
            power_data = pump.calculate_power_consumption(flow_value, density)

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

    @action(detail=False, methods=['get'])  # ИСПРАВЛЕНО: detail=True -> detail=False
    def find_suitable(self, request):
        """
        Подбор насосов по требуемым параметрам.
        """
        required_flow = request.query_params.get('required_flow')
        required_head = request.query_params.get('required_head')

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
                if (pump.left_range <= flow <= pump.right_range and
                        pump.nominal_head and  # ИСПРАВЛЕНО: niminal_head -> nominal_head
                        abs(pump.nominal_head - head) / head <= tolerance):

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
                'pumps': suitable_pumps[:10],
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
        """
        pumps = self.get_queryset()

        stats = {
            'total_pumps': pumps.count(),
            'manufacturers': list(pumps.values_list('zavod', flat=True).distinct()),  # ИСПРАВЛЕНО
            'flow_range': {
                'min': pumps.aggregate(models.Min('nominal_range'))['nominal_range__min'],
                'max': pumps.aggregate(models.Max('nominal_range'))['nominal_range__max'],
                'avg': pumps.aggregate(models.Avg('nominal_range'))['nominal_range__avg'],
            },
            'efficiency_range': {
                'min': pumps.aggregate(models.Min('max_efficiency'))['max_efficiency__min'],
                'max': pumps.aggregate(models.Max('max_efficiency'))['max_efficiency__max'],
                'avg': pumps.aggregate(models.Avg('max_efficiency'))['max_efficiency__avg'],
            },
        }

        return Response(stats)

    def _get_recommendation(self, point_data, pump):
        recommendations = []

        if point_data['is_optimal']:
            recommendations.append('Точка находится в оптимальном диапазоне работы')
        elif point_data['is_in_working_range']:
            recommendations.append('Точка в рабочем диапазоне, но не оптимальна')
        else:
            recommendations.append('Внимание! Точка вне рабочего диапазона')

        if point_data['kpd'] < pump.min_kpd_rosneft:
            recommendations.append(
                f'КПД ({point_data["kpd"]:.1f}%) ниже минимального по Роснефти '
                f'({pump.min_kpd_rosneft}%)'
            )

        if pump.max_efficiency:
            efficiency_ratio = (point_data['kpd'] / pump.max_efficiency) * 100
            if efficiency_ratio < 80:
                recommendations.append(
                    f'КПД составляет {efficiency_ratio:.1f}% от максимального '
                    f'({pump.max_efficiency:.1f}%)'
                )

        return {
            'status': 'optimal' if point_data['is_optimal'] else
            'working' if point_data['is_in_working_range'] else 'warning',
            'messages': recommendations  # ИСПРАВЛЕНО: message -> messages
        }