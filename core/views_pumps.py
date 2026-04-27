from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import PumpCharacteristic, ElectricMotor, Well
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
        return PumpCharacteristicSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

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

        min_efficiency = self.request.query_params.get('min_kpd')
        if min_efficiency:
            queryset = queryset.filter(max_efficiency__gte=float(min_efficiency))

        return queryset

    @action(detail=True, methods=['get'])
    # @action - декоратор DRF для создания кастомных эндпоинтов
    # detail = True - действие применяется к конкретному объекту (требует pk)
    # methods = ['get'] - разрешен только GET - запрос
    def characteristics(self, request, pk=None):
        """
        Получение полных характеристик насоса для построения графиков.
        """
        pump = self.get_object()  # стандартный метод DRF для получения объекта по pk

        characteristics_data = {
            'pump_info': {                           # Информация о насосе
                'id': pump.id,                       # Уникальный идентификатор насоса
                'name': pump.harka_stupen,           # Название/марка ступени
                'manufacturer': pump.zavod,          # Производитель (завод)
                'nominal_flow': pump.nominal_range,  # Номинальная подача
                'nominal_head': pump.nominal_head,   # Номинальный напор (расчетный)
                'stages': pump.stages_count,         # Количество ступеней
            },
            'characteristics': {                     # Характеристики для графиков
                'q_values': pump.q_values,           # Значения подачи (расхода) [м³/ч]
                'h_values': pump.h_values,           # Значения напора [м]
                'n_values': pump.n_values,           # Значения мощности [кВт]
                'kpd_values': pump.kpd_values,       # Значения КПД [%]
            },
            'ranges': {                                          # Рабочие диапазоны
                'working': [pump.left_range, pump.right_range],  # Рабочий диапазон [мин, макс]
                'optimal': pump.optimal_flow_range or [],        # Оптимальный диапазон (может быть None)
                'nominal': pump.nominal_range,                   # Номинальная подача (число)
            },
            'efficiency': {                            # Эффективность (КПД)
                'max': pump.max_efficiency,            # Максимальное значение КПД
                'max_flow': pump.max_efficiency_flow,  # Подача при макс. КПД
                'threshold_75_percent': pump.max_efficiency * 0.75 if pump.max_efficiency else None,
                                                       # Порог 75% от макс. КПД
            },
        }

        return Response(characteristics_data)

    @action(detail=True, methods=['get'])
    def calculate_point(self, request, pk=None):
        """
        Расчет параметров насоса в заданной точке.
        """
        pump = self.get_object()

        flow = request.query_params.get('flow')
        if not flow:
            return Response(
                {'error': 'Параметр "flow" обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flow_value = float(flow)
            density = float(request.query_params.get('density', 850.0))  # плотность

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

    @action(detail=False, methods=['get'])
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
                        pump.nominal_head and
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
                'pumps': suitable_pumps,
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
            'messages': recommendations
        }

    @action(detail=True, methods=['get'])
    def find_matching_motor(self, request, pk=None):
        """
        Поиск подходящего электродвигателя для насоса.

        Параметры запроса:
        - service_factor: коэффициент запаса (по умолчанию 1.15)
        - min_efficiency: минимальный КПД двигателя (по умолчанию 80)
        :param request: HTTP запрос
        :param pk: ID насоса
        :return: response: Список подходящих двигателей
        """
        pump = self.get_object()

        # Параметры подбора
        service_factor = float(request.query_params.get('service_factor', 1.15))
        min_efficiency = float(request.query_params.get('min_efficiency', 80.0))

        # Расчет требуемой мощности насоса при номинально подаче
        power_data = pump.calculate_power_consumption()
        required_power = power_data['shaft_power_kw'] * service_factor

        # Получаем все активные двигатели
        from .models import ElectricMotor
        motors = ElectricMotor

        # Фильтруем по мощности (с запасом ±20%)
        suitable_motors = motors.objects.filter(
            nominal_power__gte=required_power * 0.8,
            nominal_power__lte=required_power * 1.2,
            efficiency__gte=min_efficiency
        )

        # Формируем результат
        result = []
        for motor in suitable_motors:
            motor_data = {
                'id': motor.id,
                'model': motor.model,
                'manufacturer': motor.manufacturer,
                'nominal_power': motor.nominal_power,
                'efficiency': motor.efficiency,
                'power_factor': motor.power_factor,
                'vibration_level': motor.vibration_level,
                'power_match_percentage': round((motor.nominal_power / required_power) * 100, 1),
                'actual_service_factor': round(motor.nominal_power / power_data['shaft_power_kw'], 2),
                'vibration_status': motor.get_vibration_status()['status'],
                'efficiency_class': motor.calculate_efficiency_class()
            }
            result.append(motor_data)

        # Сортируем по эффективности и близости мощности
        result.sort(
            key=lambda x: (
                x['efficiency'],
                -abs(100 - x['power_match_percentage'])
            ),
            reverse=True
        )

        return Response({
            'pump': {
                'id': pump.id,
                'name': pump.harka_stupen,
                'nominal_flow': pump.nominal_range,
                'nominal_head': pump.nominal_head,
                'required_power_kw': round(required_power, 2),
                'shaft_power_kw': round(power_data['shaft_power_kw'], 2)
            },
            'selection_parameters': {
                'service_factor': service_factor,
                'min_efficiency': min_efficiency,
            },
            'found_count': len(result),
            'motors': result[:10]  # Ограничиваем 10 лучшими
        })

    @action(detail=False, methods=['get'])
    def select_for_well(self, request):
        """
        Подбор оптимальной пары насос+двигатель для скважины
        """
        well_id = request.query_params.get('well_id')
        if not well_id:
            return Response(
                {'error': 'Не указан ID скважины'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            well = Well.objects.get(id=well_id)
        except Well.DoesNotExist:
            return Response(
                {'error': f'Скважина с ID {well_id} не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )

        # --- Получение параметров из запроса ---
        target_flow = request.query_params.get('target_flow')
        if target_flow:
            try:
                target_flow = float(target_flow)
            except ValueError:
                return Response(
                    {'error': 'Некорректное значение целевого расхода'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_flow = well.get_recommended_flow()

        # Проверка реалистичности дебита
        max_flow = well.get_max_possible_flow()
        if max_flow and target_flow > max_flow:
            return Response({
                'error': f'Запрошенный дебит {target_flow:.1f} м³/сут превышает максимально возможный {max_flow:.1f} м³/сут',
                'well_id': well.id,
                'max_possible_flow': max_flow
            }, status=status.HTTP_400_BAD_REQUEST)

        # Коэффициент запаса
        service_factor = request.query_params.get('service_factor', '1.15')
        try:
            service_factor = float(service_factor.replace(',', '.'))
        except ValueError:
            service_factor = 1.15

        # Давление на приеме (опционально)
        intake_pressure = request.query_params.get('intake_pressure')
        if intake_pressure:
            try:
                intake_pressure = float(intake_pressure)
            except ValueError:
                intake_pressure = None
        else:
            intake_pressure = None

        # --- Расчет потребного напора ---
        required_head = well.calculate_required_head(target_flow, intake_pressure)

        # Глубина спуска насоса
        pump_depth = well.get_pump_depth(target_flow, intake_pressure)

        # Свойства жидкости на приеме
        if intake_pressure is None:
            P_intake = well.get_min_intake_pressure()
        else:
            P_intake = intake_pressure

        fluid_props = well.get_fluid_properties_at_intake(target_flow, P_intake)

        # --- Поиск подходящих насосов ---
        suitable_pumps = PumpCharacteristic.objects.filter(
            is_active=True,
            left_range__lte=target_flow,
            right_range__gte=target_flow
        )

        results = []
        for pump in suitable_pumps:
            pump_params = pump.calculate_at_point(target_flow)

            pump_head = pump_params['h']

            if pump_head < required_head * 0.95:  # допуск 5%
                continue
            if pump_head > required_head * 1.3:  # запас >30% - неэкономично
                continue

            # Расчет мощности
            power_data = pump.calculate_power_consumption(target_flow)
            required_power = power_data['shaft_power_kw'] * service_factor

            # Поиск двигателя
            suitable_motors = ElectricMotor.objects.filter(
                is_active=True,
                nominal_power__gte=required_power * 0.85,
                nominal_power__lte=required_power * 1.2
            ).order_by('-efficiency')

            best_motor = suitable_motors.first()

            if best_motor:
                overall_efficiency = round(
                    (pump_params['kpd'] / 100) * (best_motor.efficiency / 100) * 100,
                    1
                )

                results.append({
                    'pump': {
                        'id': pump.id,
                        'name': pump.harka_stupen,
                        'nominal_flow': pump.nominal_range,
                        'working_range': [pump.left_range, pump.right_range],
                    },
                    'pump_at_point': {
                        'flow': pump_params['q'],
                        'head': pump_params['h'],
                        'power': pump_params['n'],
                        'efficiency': pump_params['kpd']
                    },
                    'motor': {
                        'id': best_motor.id,
                        'model': best_motor.model,
                        'power': best_motor.nominal_power,
                        'efficiency': best_motor.efficiency,
                        'service_factor': round(
                            best_motor.nominal_power / power_data['shaft_power_kw'], 2
                            ) if power_data['shaft_power_kw'] and power_data['shaft_power_kw'] > 0 else 0
                    },
                    'overall_efficiency': overall_efficiency
                })

        results.sort(key=lambda x: x['overall_efficiency'], reverse=True)

        return Response({
            'well': {
                'id': well.id,
                'name': well.name,
                'depth': well.depth,
                'reservoir_pressure': well.reservoir_pressure,
                'productivity_index': well.productivity_index,
                'water_cut': well.water_cut,
                'pump_depth': pump_depth
            },
            'selection_parameters': {
                'target_flow': target_flow,
                'required_head': required_head,
                'service_factor': service_factor,
                'intake_pressure': round(P_intake, 2),
                'gas_fraction': round(fluid_props['gas_fraction'] * 100, 1)
            },
            'found_count': len(results),
            'recommendations': results[:10]
        })
