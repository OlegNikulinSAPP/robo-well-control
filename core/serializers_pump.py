from rest_framework import serializers
from .models import PumpCharacteristic


class PumpCharacteristicSerializer(serializers.ModelSerializer):
    """
    Сериализатор для характеристик насосов ЭЦН.

    Предоставляет полный доступ к данным насосов через REST API.
    Включает как основные параметры, так и характеристики для построения графиков.
    """
    # Вычисляемые поля для удобства API
    max_efficiency_display = serializers.SerializerMethodField()
    optimal_range_display = serializers.SerializerMethodField()
    characteristics_summary = serializers.SerializerMethodField()

    class Meta:
        model = PumpCharacteristic
        fields = "__all__"
        read_only_fields = (
            'created_at',
            'updated_at',
            'max_efficiency',
            'max_efficiency_flow',
            'optimal_flow_range'
        )

    def get_max_efficiency_display(self, obj):
        """
        Форматированное отображение максимального КРД.

        Args:
            obj: Объект PumpCharacteristic

        Returns:
            str: Отформатированная строка
        """
        if obj.max_efficiency and obj.max_efficiency_flow:
            return f'{obj.max_efficiency:.1f}% при {obj.max_efficiency_flow:.0f} м³/сут'
        return 'Не рассчитано'

    def get_optimal_range_display(self, obj):
        """
        Форматированное отображение оптимального диапазона.

        Args:
            obj: Объект PumpCharacteristic

        Returns:
            str: Отформатированная строка
        """
        if obj.optimal_flow_range and len(obj.optimal_flow_range) == 2:
            return f'{obj.optimal_flow_range[0]:.0f} - {obj.optimal_flow_range[1]:.0f} м³/сут'
        return 'Не рассчитан'

    def get_characteristics_summary(self, obj):  # Исправлено: characteristics (множественное число)
        """
        Сводка характеристик насоса.

        Args:
            obj: Объект PumpCharacteristic

        Returns:
            dict: Сводная информация
        """
        summary = {
            'points_count': len(obj.q_values) if obj.q_values else 0,
            'working_range': {
                'min': obj.left_range,
                'nominal': obj.nominal_range,
                'max': obj.right_range
            },
            'head_at_nominal': obj.nominal_head,
            'stages': obj.stages_count
        }

        if obj.kpd_values:
            summary['efficiency_range'] = {
                'min': min(obj.kpd_values),
                'max': obj.max_efficiency if obj.max_efficiency else max(obj.kpd_values)
            }
        return summary

    def validate_q_values(self, value):
        """
        Валидация массива значений подачи.

        Args:
            value: Массив значений

            Returns:
                list: Проверенный массив

            Raises:
                serializers.ValidationError: Если данные некорректны
        """
        if not isinstance(value, list):
            raise serializers.ValidationError('Q_values должен быть списком')
        if len(value) < 3:
            raise serializers.ValidationError('Должно быть не менее 3 точек характеристики')

        # Проверяем, что значения возрастают
        for i in range(1, len(value)):
            if value[i] <= value[i - 1]:
                raise serializers.ValidationError(
                    f'Значения подачи должны возрастать. Ошибка на позиции {i}:'
                    f'{value[i - 1]} → {value[i]}'
                )
        return value

    def validate(self, data):
        """
        Валидация всех данных насоса.

        Args:
            data: Данные для валидации

        Returns:
            dict: Проверенные данные

        Raises:
            serializers.ValidationError: Если данные некорректны
        """

        # Проверяем соответствие длин массивов
        array_fields = ['q_values', 'h_values', 'n_values', 'kpd_values']
        lengths = []

        for field in array_fields:
            if field in data and data[field]:
                lengths.append(len(data[field]))

        if lengths and len(set(lengths)) > 1:
            raise serializers.ValidationError(
                f'Все массивы характеристик должны иметь одинаковую длину'
                f'Получены длины: {dict(zip(array_fields, lengths))}'
            )

        # Проверяем, что номинальная подача находится в рабочем диапазоне
        if 'nominal_range' in data and 'left_range' in data and 'right_range' in data:
            if not (data['left_range'] <= data['nominal_range'] <= data['right_range']):
                raise serializers.ValidationError(
                    f'Номинальная подача ({data["nominal_range"]}) должна находиться'
                    f'в рабочем диапазоне [{data["left_range"]}, {data["right_range"]}]'
                )

        return data

    def to_representation(self, instance):
        """
        Кастомизация вывода JSON.

        Args:
            instance: Объект модели

        Returns:
            dict: Словарь с данными для JSON
        """
        representation = super().to_representation(instance)

        # Добавляем вычисляемые поля
        representation['max_efficiency_display'] = self.get_max_efficiency_display(instance)
        representation['optimal_range_display'] = self.get_optimal_range_display(instance)
        representation['characteristics_summary'] = self.get_characteristics_summary(instance)  # Исправлено

        # Форматируем технические характеристики
        if representation.get('nominal_head'):
            representation['nominal_head_display'] = f'{representation["nominal_head"]:.0f} м'  # Добавлено форматирование
        if representation.get('stages_count'):
            representation['stages_display'] = f'{representation["stages_count"]} ступеней'

        return representation


class PumpCharacteristicListSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для списка насосов.

    Используется при выводе списка насосов для уменьшения объема данных.
    Включает только основные поля без полных характеристик.
    """
    optimal_range = serializers.SerializerMethodField()
    max_efficiency_display = serializers.SerializerMethodField()
    nominal_head_display = serializers.SerializerMethodField()

    class Meta:
        model = PumpCharacteristic
        fields = [
            'id',
            'cod',
            'harka_stupen',
            'zavod',
            'material_stupen',
            'nominal_range',
            'nominal_head',
            'nominal_head_display',
            'max_efficiency',
            'max_efficiency_display',
            'max_efficiency_flow',
            'optimal_range',
            'stages_count',
            'housing_diameter',
            'left_range',
            'right_range',
            'min_kpd_rosneft',
            'is_active'
        ]

    def get_optimal_range(self, obj):
        """
        Получение оптимального диапазона работы.

        Args:
            obj: объект насоса

        Returns:
            list: оптимальный диапазон
        """
        return obj.optimal_flow_range if obj.optimal_flow_range else []

    def get_max_efficiency_display(self, obj):
        """
        Форматированное отображение максимального КПД.

        Args:
            obj: объект насоса

        Returns:
            str: отформатированная строка
        """
        if obj.max_efficiency and obj.max_efficiency_flow:
            return f'{obj.max_efficiency:.1f}% при {obj.max_efficiency_flow:.0f} м³/сут'
        return None

    def get_nominal_head_display(self, obj):
        """
        Форматированное отображение номинального напора.

        Args:
            obj: объект насоса

        Returns:
            str: отформатированная строка
        """
        if obj.nominal_head:
            return f'{obj.nominal_head:.0f} м'
        return None

    def to_representation(self, instance):
        """
        Кастомизация вывода для списка.

        Args:
            instance: объект насоса

        Returns:
            dict: словарь с данными
        """
        representation = super().to_representation(instance)
        # super().to_representation() → только поля из Meta.fields

        # Добавляем флаг, есть ли полные характеристика
        representation['has_full_characteristics'] = (
                bool(instance.q_values) and
                bool(instance.h_values) and
                bool(instance.n_values) and
                bool(instance.kpd_values)
        )

        # Добавляем количество точек характеристик
        if instance.q_values:
            representation['characteristic_points'] = len(instance.q_values)

        # Наш to_representation() → поля из Meta.fields + наши добавки
        return representation

