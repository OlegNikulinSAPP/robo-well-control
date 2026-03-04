# Импорт - механизм включения внешних модулей и классов в текущее пространство имен
from rest_framework import serializers
from .models import ElectricMotor


# Наследование (Inheritance) - механизм ООП, позволяющий классу наследовать функциональность
# родительского класса
class ElectricMotorSerializer(serializers.ModelSerializer):
    # Документирование кода - описание назначения класса для других разработчиков
    """
    Сериализатор для электродвигателей ЭЦН
    """
    # SerializerMethodField - поле сериализатора, значение которого вычисляется динамически
    # через метод get_<field_name>
    # Вычисляемые поля
    rated_torque_display = serializers.SerializerMethodField()
    # Вычисляемые поля - поля, значения которых не хранятся в БД, а рассчитываются на основе других полей модели
    starting_current_ratio_display = serializers.SerializerMethodField()  # кратность пускового тока
    # Агрегация данных - объединение нескольких характеристик в один вычисляемый показатель
    vibration_status_display = serializers.SerializerMethodField()
    efficiency_class_display = serializers.SerializerMethodField()
    power_consumption_summary = serializers.SerializerMethodField()
    technical_summary = serializers.SerializerMethodField()

    class Meta:
        model = ElectricMotor
        fields = "__all__"
        read_only_field = ('created_at', 'updated_at')

    # Методы get_(Getter Methods) - специальные методы, которые DRF автоматически вызывает для полей
    # типа SerializerMethodField
    def get_rated_torque_display(self, obj):
        """
        Расчет и форматирование номинального момента
        :param obj: Объект ElectricMotor
        :return: str: Отформатированная строка
        """
        torque_nm = obj.calculate_rated_torque()
        return f'{torque_nm:.1f} Нм ({obj.torque} кгс.см)'

    def get_starting_current_ratio_display(self, obj):
        """
        Расчет и форматирование кратности пускового момента
        :param obj: Объект ElectricMotor
        :return: str: Отформатированная строка
        """
        ratio = obj.calculate_starting_current_ratio()
        return f'{ratio:.1f} (Iпуск/Iном)'

    def get_vibration_status_display(self, obj):
        """
        Получение статуса вибрации
        :param obj: Объект ElectricMotor
        :return: dict: Статус и рекомендации
        """
        return obj.get_vibration_status()

    def get_efficiency_class_display(self, obj):
        """
        Получение класса энергоэффективности
        :param obj: Объект ElectricMotor
        :return: str: Класс IE
        """
        return obj.calculate_efficiency_class()

    def get_power_consumption_summary(self, obj):
        """
        Расчет потребления электроэнергии
        :param obj: Объект ElectricMotor
        :return: dict: Результаты расчета
        """
        return obj.calculate_power_consumption()

    def get_technical_summary(self, obj):
        """
        Сводка технических характеристик
        :param obj: Объект ElectricMotor
        :return: dict: Сводная информация
        """
        return obj.get_technical_summary()

    # Валидация на уровне поля - проверка конкретного поля с помощью метода validate_<field_name>
    def validate_nominal_power(self, value):
        """
        Валидация номинальной мощности
        :param value: Значение мощности
        :return: float: Проверенное значение
        :raise: serializers.ValidationError: Если мощность некорректна
        """
        if value <= 0:
            raise serializers.ValidationError('Мощность должна быть положительным числом')
        if value > 1000:
            raise serializers.ValidationError('Мощность не может превышать 1000 кВт')

        return value

    def validate_nominal_voltage(self, value):
        """
        Валидация номинального напряжения
        :param value: Значение напряжения
        :return: float: Проверенное значение
        """
        if value <= 0:
            raise serializers.ValidationError('Напряжение должно быть положительным числом')
        if value > 10000:
            raise serializers.ValidationError('Напряжение не может превышать 10 000 В')
        # Сквозная валидация - после успешных проверок значение передается дальше в сериализатор
        return value

    def validate_efficiency(self, value):
        """
        Валидация КПД.
        :param value: Значение КПД.
        :return: float: Проверенное значение
        """
        if value < 0 or value > 100:
            raise serializers.ValidationError('КПД должен быть в диапазоне 0-100%')

        return value

    def validate_power_factor(self, value):
        """
        Валидация коэффициента мощности.
        :param value: Значение cosφ
        :return: Проверенное значение
        """
        if value < 0 or value > 1:
            raise serializers.ValidationError('Коэффициент мощности должен быть в диапазоне 0-1')

        return value

    # Объектная валидация - проверка взаимосвязей между несколькими полями модели через метод validate()
    def validate(self, data):
        """
        Валидация всех данных двигателя.
        :param data: Данные для валидации
        :return: dict: Проверенные данные
        :raises: serializers.ValidationError: Если данные некорректны
        """
        if 'acceleration_voltage' in data and 'nominal_voltage' in data:
            if data['acceleration_voltage'] > 0 and data['acceleration_voltage'] > data['nominal_voltage']:
                raise serializers.ValidationError(
                    f'Напряжение разгона ({data["acceleration_voltage"]})'
                    f'должно быть ниже номинального ({data["nominal_voltage"]} В)'
                )

        if 'short_circuit_current' in data and 'nominal_current' in data:
            if 0 < data['short_circuit_current'] <= data['nominal_current']:
                raise serializers.ValidationError(
                    f'Ток КЗ ({data["short_circuit_current"]} А)'
                    f'должен быть больше номинального ({data["nominal_current"]} A)'
                )

        if 'vibration_level' in data and data['vibration_level'] > 10:
            raise serializers.ValidationError(
                f'Уровень вибрации ({data["vibration_level"]} мм/с) слишком высок'
            )

        return data

    def to_representation(self, instance):
        """
        Кастомизация вывода JSON.
        :param instance: Объект модели
        :return: dict: Словарь с данными для JSON
        """
        representation = super().to_representation()

        # Добавляем вычисляемые поля
        representation['rated_torque_display'] = self.get_rated_torque_display(instance)
        representation['starting_current_ratio_display'] = self.get_starting_current_ratio_display(instance)
        representation['vibration_status_display'] = self.get_vibration_status_display(instance)
        representation['efficiency_class_display'] = self.get_efficiency_class_display(instance)
        representation['power_consumption_summary'] = self.get_power_consumption_summary(instance)
        representation['technical_summary'] = self.get_technical_summary(instance)

        # Приватные методы - методы с префиксом _, предназначенные для внутреннего использования
        # внутри класса
        # Форматируем числовые значения
        self._format_numeric_values(representation)

        # Добавляем флаги состояния
        representation['status_flags'] = {
            'vibration_ok': instance.vibration_level < 6,
            'insulation_ok': instance.insulation_resistance >= 2000,
            'efficiency_ok': instance.efficiency >= 80,
            'overall_condition': self._assess_overal_condition(instance)
        }

        return representation

    def _format_numeric_values(self, representation):
        """
        Форматирование числовых значений для отображения.
        :param representation: Словарь представления
        """
        format_map = {
            'nominal_power': (' кВт', 1),
            'nominal_voltage': (' В', 0),
            'nominal_current': (' А', 1),
            'rotation_speed': (' об/мин', 0),
            'torque': (' кгс.см', 1),
            'shaft_torque': (' кгс.см', 2),
            'vibration_level': (' мм/с', 1),
            'efficiency': ('%', 1),
            'slip': ('%', 1),
        }

        # Распаковка кортежей - извлечение единиц измерения и количества знаков для каждого поля
        for field, (unit, decimal) in format_map.items():
            if field in representation and representation[field] is not None:
                value = representation[field]
                formatted = f'{value:.{decimal}f}{unit}'
                representation[f'{field}_display'] = formatted

    def _assess_overall_condition(self, motor):
        """
        Общая оценка состояния двигателя.
        :param motor: Объект двигателя
        :return: str: Общая оценка
        """
        issues = []
        if motor.vibration_level > 4.5:
            issues.append('вибрация')
        if motor.insulation_resistance < 2000:
            issues.append('изоляция')
        if motor.efficiency < 80:
            issues.append('КПД')
        if not issues:
            return 'Отличное'
        elif len(issues) == 1:
            return f'Хорошее (проблема: {issues[0]})'
        else:
            return f'Требует внимания (проблема: {" ,".join(issues)})'


class ElectricMotorListSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для списка электродвигателей.

    Используется при выводе списка для уменьшения объема данных.
    Включает только ключевые параметры и основные расчетные поля
    """
    power_consumption_daily = serializers.SerializerMethodField()
    condition_summary = serializers.SerializerMethodField()

    class Meta:
        model = ElectricMotor
        fields = [
            'id',
            'motor_id',
            'model',
            'manufacturer',
            'nominal_power',
            'nominal_voltage',
            'nominal_current',
            'rotation_speed',
            'efficiency',
            'power_factor',
            'vibration_level',
            'insulation_resistance',
            'power_consumption_daily',
            'condition_summary',
            'is_active'
        ]

    def get_power_consumption_daily(self, obj):
        """
        Расчет суточного потребления.
        :param obj: Объект ElectricMotor
        :return: dict: Данные о потреблении
        """
        consumption = obj.calculate_power_consumption()

        return {
            'daily_kwh': round(consumption['daily_consumption_kwh'], 1),
            'monthly_kwh': round(consumption['monthly_consumption_kwh'], 1),
            'active_power_kw': round(consumption['active_power_kw'], 2)
        }

    def get_condition_summary(self, obj):
        """
        Сводка состояния двигателя.
        :param obj: Объект ElectricMotor
        :return: dict: Сводка состояния
        """
        vibration_status = obj.get_vibration_status()

        if obj.insulation_resistance >= 2000:
            insulation_status = 'отличное'
            insulation_color = 'green'
        elif obj.insulation_resistance >= 1500:
            insulation_status = 'хорошее'
            insulation_color = 'blue'
        elif obj.insulation_resistance >= 1000:
            insulation_status = 'удовлетворительное'
            insulation_color = 'yellow'
        else:
            insulation_status = 'критическое'
            insulation_color = 'red'

        # Общая оценка
        issues = []

        if obj.vibration_level > 4.5:
            issues.append('вибрация')
        if obj.insulation_resistance < 1000:
            issues.append('изоляция')
        if obj.efficiency < 80:
            issues.append('КПД')

        if not issues:
            overall = 'отличное'
            overall_color = 'green'
        elif len(issues) == 1:
            overall = 'хорошее'
            overall_color = 'blue'
        else:
            overall = 'требует внимания'
            overall_color = 'yellow'

        return {
            'vibration': {
                'level': obj.vibration_level,
                'status': vibration_status['status'],
                'color': vibration_status['color'],
                'recommendation': vibration_status['recommendation']
            },
            'insulation': {
                'resistance': obj.insulation_resistance,
                'status': insulation_status,
                'color': insulation_color
            },
            'efficiency': {
                'value': obj.efficiency,
                'class': obj.calculate_efficiency_class()
            },
            'overall': {
                'status': overall,
                'color': overall_color,
                'issues': issues
            }
        }

    def to_representation(self, instance):
        """
        Кастомизация вывода для списка.
        :param instance: Объект модели
        :return: dict: Словарь с данными
        """
        representation = super().to_representation(instance)

        representation['nominal_power_display'] = f'{representation["nominal_power"]} кВт'
        representation['nominal_voltage_display'] = f'{representation["nominal_voltage"]} В'
        representation['nominal_current_display'] = f'{representation["nominal_current"]} А'
        representation['efficiency_display'] = f'{representation["efficiency"]}%'
        representation['vibration_display'] = f'{representation["vibration_level"]} мм/с'
        representation['efficiency_class'] = instance.calculate_efficiency_class()

        return representation
