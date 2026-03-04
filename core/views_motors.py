from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import ElectricMotor
from .serializers_motors import ElectricMotorSerializer, ElectricMotorListSerializer


class ElectricMotorViewSet(viewsets.ModelViewSet):
    """
    ViewSet для обработки операций CRUD с электродвигателями ЭЦН

    Предоставляет полный набор REST API для работы с электродвигателями:
    - просмотр списка и деталей двигателей
    - фильтрация и поиск по параметрам
    - технические расчеты и анализ
    - подбор двигателей по мощности
    """
    queryset = ElectricMotor.objects.filter(is_active=True)
    serializer_class = ElectricMotorSerializer
    # Filter Backends — компоненты DRF, которые обрабатывают параметры запроса
    # для фильтрации, поиска и сортировки.
    # Подключаем три бэкенда:
    # DjangoFilterBackend — точная фильтрация по полям
    # SearchFilter — текстовый поиск
    # OrderingFilter — сортировка результатов
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Указываем поля, по которым можно фильтровать через ?manufacturer=... и ?nominal_voltage=...
    # Фильтры
    filterset_fields = [
        'manufacturer',
        'nominal_voltage',
    ]

    # Text Search — поиск по частичному совпадению в текстовых полях.
    # При запросе ?search=... будет искать в модели, производителе и ID двигателя.
    # Поиск
    search_fields = [
        'model',
        'motor_id',
        'manufacturer',
    ]

    # Ordering — возможность сортировки результатов по указанным полям.
    # Разрешаем сортировку по модели, мощности, напряжению, КПД, вибрации и дате
    # создания через ?ordering=...
    # Сортировка
    ordering_fields = [
        'model',
        'nominal_power',
        'nominal_voltage',
        'efficiency',
        'vibration_level',
        'created_at',
    ]

    # Default Ordering — порядок сортировки, применяемый, если клиент не указал свой.
    # По умолчанию сортируем сначала по модели, затем по мощности (возрастание).
    ordering = ['model', 'nominal_power']

    def get_serializer_class(self):
        """
        Выбор сериализатора в зависимости от действия.
        :return: Serializer: Выбранный сериализатор
        """
        if self.action == 'list':
            return ElectricMotorListSerializer
        return ElectricMotorSerializer

    def get_queryset(self):
        """
        Фильтрация QuerySet по параметрам запроса.
        :return: QuerySet: Отфильтрованный набор двигателей
        """
        queryset = super().get_queryset()

        # Фильтрация по мощности
        min_power = self.request.query_params.get('min_power')
        max_power = self.request.query_params.get('max_power')
        if min_power:
            queryset = queryset.filter(nominal_power__gte=float(min_power))
        if max_power:
            queryset = queryset.filter(nominal_power__lte=float(max_power))

        # Фильтрация по КПД - ИСПРАВЛЕНО
        min_efficiency = self.request.query_params.get('min_efficiency')
        if min_efficiency:
            queryset = queryset.filter(efficiency__gte=float(min_efficiency))  # было min_efficiency__gte

        # Фильтрация по напряжению
        voltage = self.request.query_params.get('voltage')
        if voltage:
            voltage_value = float(voltage)
            queryset = queryset.filter(
                nominal_voltage__gte=voltage_value * 0.9,
                nominal_voltage__lte=voltage_value * 1.1
            )

        # Фильтрация по вибрации
        max_vibration = self.request.query_params.get('max_vibration')
        if max_vibration:
            queryset = queryset.filter(vibration_level__lte=float(max_vibration))

        return queryset

    @action(detail=True, methods=['get'])
    def technical_analysis(self, request, pk=None):
        """
        Технический анализ двигателя.
        :param request: HTTP запрос
        :param pk: ID двигателя
        :return: response: Результаты анализа
        """
        # get_object() — встроенный метод ViewSet, который получает объект по pk
        # из URL или возвращает 404
        motor = self.get_object()

        analysis = {
            'motor_info': {
                'id': motor.id,
                'model': motor.model,
                'manufacturer': motor.manufacturer,
                'nominal_power': motor.nominal_power,
                'nominal_voltage': motor.nominal_voltage,
            },
            'calculations': {
                'rated_torque_nm': motor.calculate_rated_torque(),
                'starting_current_ratio': motor.calculate_starting_current_ratio(),
                'power_consumption': motor.calculate_power_consumption(),
            },
            'assessments': {
                'vibration': motor.get_vibration_status(),
                'efficiency_class': motor.calculate_efficiency_class(),
                'insulation_status': self._assess_insulation(motor),
            },
            'recommendations': self._generate_recommendations(motor)
        }

        return Response(analysis)

    @action(detail=True, methods=['get'])
    def compare_with_standard(self, request, pk=None):
        """
        Сравнение с ГОСТ стандартами.
        :param request: HTTP зарос
        :param pk: ID двигателя
        :return: response: Сравнение со стандартами
        """
        motor = self.get_object()

        standards = {
            'efficiency': self._check_efficiency_standard(motor),
            'vibration': self._check_vibration_standard(motor),
            'insulation': self._check_insulation_standard(motor),
            'starting_current': self._check_starting_current_standard(motor),
        }

        # Общая оценка
        passed_checks = sum(1 for check in standards.values() if check['passed'])
        total_checks = len(standards)

        # Вычисляем процент пройденных проверок от общего количества
        standards['summary'] = {
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'compliance_percentage': (passed_checks / total_checks) * 100 if total_checks > 0 else 0,
            'status': 'соответствует' if passed_checks == total_checks else 'частично соответствует'
        }

        return Response(standards)

    @action(detail=False, methods=['get'])
    def find_for_pump(self, request):
        """
        Подбор двигателей для насоса.

        Параметры запроса:
        - pump_power: требуемая мощность насоса, кВт
        - voltage: напряжение сети, В
        - service_factor: коэффициент запаса (по умолчанию 1.15)
        - min_efficiency: минимальный КПД, % (по умолчанию 80)
        :param request: HTTP запрос
        :return: response: Подходящие двигатели
        """

        pump_power = request.query_params.get('pump_power')
        voltage = request.query_params.get('voltage')

        if not pump_power:
            return Response(
                {'error': 'Параметр "pump_power" обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            pump_power_value = float(pump_power)
            voltage_value = float(voltage) if voltage else None

            service_factor = float(request.query_params.get('service_factor', 1.15))
            min_efficiency = float(request.query_params.get('min_efficiency', 80))

            # Расчет требуемой мощности двигателя
            required_power = pump_power_value * service_factor

            # Базовый запрос - ИСПРАВЛЕНО: убраны фигурные скобки и исправлены имена полей
            queryset = self.get_queryset().filter(
                nominal_power__gte=required_power * 0.9,
                nominal_power__lte=required_power * 1.2,
                efficiency__gte=min_efficiency  # ИСПРАВЛЕНО: efficiency, а не min_efficiency
            )

            # Фильтрация по напряжению если указано
            if voltage_value:
                # Допуск ±10%
                queryset = queryset.filter(
                    nominal_voltage__gte=voltage_value * 0.9,
                    nominal_voltage__lte=voltage_value * 1.1
                )

            suitable_motors = []

            for motor in queryset:
                motor_data = ElectricMotorListSerializer(motor).data
                motor_data['power_match_percentage'] = round(
                    (motor.nominal_power / required_power) * 100, 1
                )
                motor_data['service_factor_actual'] = round(
                    motor.nominal_power / pump_power_value, 2
                )
                motor_data['vibration_status'] = motor.get_vibration_status()
                suitable_motors.append(motor_data)

            # Сортируем по КПД (по убыванию) и близости мощности
            suitable_motors.sort(
                key=lambda x: (x['efficiency'], -abs(100 - x['power_match_percentage'])),
                reverse=True
            )

            return Response({
                'search_parameters': {
                    'pump_power_kw': pump_power_value,
                    'required_motor_power_kw': required_power,
                    'service_factor': service_factor,
                    'min_efficiency': min_efficiency,
                    'voltage': voltage_value
                },
                'found_count': len(suitable_motors),
                'motors': suitable_motors[:10]  # Ограничиваем 10 лучшими
            })

        except ValueError as e:
            return Response(
                {'error': f'Неверный формат параметров: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @ action(detail=False, methods=['get'])
    def efficiency_statistics(self, request):
        """
        Статистика по КПД двигателей.
        :param request: HTTP запрос
        :return: response: Статистические данные
        """
        motors = self.get_queryset()

        stats = {
            'total_motors': motors.count(),
            'manufacturers': list(motors.values_list('manufacturer', flat=True).distinct()),
            'efficiency': {
                'min': motors.aggregate(models.Min('efficiency'))['efficiency__min'],
                'max': motors.aggregate(models.Max('efficiency'))['efficiency__max'],
                'avg': motors.aggregate(models.Avg('efficiency'))['efficiency_avg'],
            },
            'power_range': {
                'min': motors.aggregate(models.Min('nominal_power'))['nominal_power__min'],
                'max': motors.aggregate(models.Max('nominal_power'))['nominal_power__max'],
                'avg': motors.aggregate(models.Avg('nominal_power'))['nominal_power__avg'],
            },
            'efficiency_classes': self._calculate_efficiency_classes(motors),
            'vibration_distribution': self._calculate_vibration_distribution(motors),
        }

        return Response(stats)

    def _assess_insulation(self, motor):
        """
        Оценка состояния изоляции.
        :param motor: Объект двигателя
        :return: dict: Оценка изоляции
        """
        if motor.insulation_resistance >= 2000:
            status = 'Отличное'
            color = 'green'
        elif motor.insulation_resistance >= 1500:
            status = 'Хорошее'
            color = 'blue'
        elif motor.insulation_resistance >= 1000:
            status = 'Удовлетворительное'
            color = 'yellow'
        else:
            status = 'Требует проверки'
            color = 'red'

        return {
            'resistance_mohm': motor.insulation_resistance,
            'status': status,
            'color': color,
            'test_voltage_v': motor.insulation_test_voltage,
        }

    def _check_efficiency_standard(self, motor):
        """
        Проверка соответствия КПД стандартам
        :param motor: Объект двигателя
        :return: dict: Результат проверки
        """
        # Минимальные требования по ГОСТ Р 51677-2000
        min_requirements = {
            16: 81.0,  # кВт: мин КПД %
            22: 81.0,
            28: 81.0,
            32: 81.0,
            40: 81.5,
            45: 81.0,
            50: 81.0,
            56: 81.0,
        }

        # Находим ближайшую мощность
        power = motor.nominal_power
        closest_power = min(min_requirements.keys(), key=lambda x: abs(x - power))
        required_efficiency = min_requirements[closest_power]
        passed = motor.efficiency >= required_efficiency

        return {
            'parameter': 'КПД',
            'actual_value': motor.efficiency,
            'required_value': required_efficiency,
            'standard': 'ГОСТ Р 51677-2000',
            'passed': passed,
            'message': f'Требуется: {required_efficiency}%, фактически: {motor.efficiency}%'
        }

    def _check_vibration_standard(self, motor):
        """
        Проверка вибрации по ГОСТ ISO 10816.
        :param motor: Объект двигателя.
        :return: dict: Результат проверки
        """
        # Допустимые уровни вибрации для электродвигателей
        max_allowed = 6  # мм/с для электродвигателей

        passed = motor.vibration_level <= max_allowed

        return {
            'parameter': 'Вибрация',
            'actual_value': motor.vibration_level,
            'required_value': max_allowed,
            'standard': 'ГОСТ ISO 10816',
            'passed': passed,
            'message': f'Допустимо: {max_allowed} мм/с, фактически: {motor.vibration_level} мм/с'
        }

    def _check_insulation_standard(self, motor):
        """
        Проверка изоляции по ГОСТ.
        :param motor: Объект двигателя.
        :return: dict: Результат проверки
        """
        # Минимальное сопротивление изоляции
        min_resistance = 2000  # МОм

        passed = motor.insulation_resistance >= min_resistance

        return {
            'parameter': 'Сопротивление изоляции',
            'actual_value': motor.insulation_resistance,
            'required_value': min_resistance,
            'standard': 'ГОСТ 183-74',
            'passed': passed,
            'message': f'Требуется: {min_resistance} МОм, фактически: {motor.insulation_resistance} МОм'
        }

    def _check_starting_current_standard(self, motor):
        """
        Проверка пускового тока.
        :param motor: Объект двигателя.
        :return: dict: Результат проверки
        """
        # Обычно пусковой ток не должен превышать 7-8 кратный
        max_ratio = 8.0

        ratio = motor.calculate_starting_current_ratio()
        passed = ratio <= max_ratio

        return {
            'parameter': 'Кратность пускового тока',
            'actual_value': round(ratio, 1),
            'required_value': max_ratio,
            'standard': 'Типовые требования',
            'passed': passed,
            'message': f'Допустимо: {max_ratio}, фактически: {ratio:.1f}'
        }

    def _generate_recommendations(self, motor):
        """
        Генерация рекомендаций по эксплуатации.
        :param motor: Объект двигателя
        :return: list: Список рекомендаций
        """
        recommendations = []

        # Проверка вибрации
        vibration_status = motor.get_vibration_status()
        if vibration_status['status'] in ['Требует внимания', 'Критическое']:
            recommendations.append({
                'type': 'warning',
                'message': f'Высокий уровень вибрации: {motor.vibration_level} мм/с',
                'action': 'Требуется проверка подшипников'
            })

        # Проверка изоляции
        if motor.insulation_resistance < 1000:
            recommendations.append({
                'type': 'warning',
                'message': f'Низкое сопротивление изоляции: {motor.insulation_resistance} МОм',
                'action': 'Рекомендуется сушка обмоток'
            })

        # Проверка КПД
        if motor.efficiency < 80:
            recommendations.append({
                'type': 'info',
                'message': f'Низкий КПД: {motor.efficiency}%',
                'action': 'Рассмотреть замену на более эффективную модель'
            })

        # Проверка нагрева
        if motor.heated_waste > motor.nominal_power * 0.05:
            recommendations.append({
                'type': 'warning',
                'message': f'Высокие потери на нагрев: {motor.heated_waste} кВт',
                'action': 'Проверить систему охлаждения'
            })

        return recommendations

    def _calculate_efficiency_classes(self, queryset):
        """
        Расчет распределения по классам энергоэффективности.
        :param queryset: QuerySet двигателей
        :return: dict: Распределение по классам
        """
        classes = {'IE1': 0, 'IE2': 0, 'IE3': 0, 'below': 0}

        for motor in queryset:
            if motor.efficiency >= 90:
                classes['IE3'] += 1
            elif motor.efficiency >= 85:
                classes['IE2'] += 1
            elif motor.efficiency >= 80:
                classes['IE1'] += 1
            else:
                classes['below'] += 1

        return classes

    def _calculate_vibration_distribution(self, queryset):
        """
        Расчет распределения по уровням вибрации.
        :param queryset: QuerySet двигателей
        :return: dict: Распределение по уровням
        """
        distribution = {
            'excellent': 0,  # ≤ 2.8 мм/с
            'good': 0,  # ≤ 4.5 мм/с
            'satisfactory': 0,  # ≤ 7.1 мм/с
            'attention': 0,  # > 7.1 мм/с
        }

        for motor in queryset:
            if motor.vibration_level <= 2.8:
                distribution['excellent'] += 1
            elif motor.vibration_level <= 4.5:
                distribution['good'] += 1
            elif motor.vibration_level <= 7.1:
                distribution['satisfactory'] += 1
            else:
                distribution['attention'] += 1

        return distribution
