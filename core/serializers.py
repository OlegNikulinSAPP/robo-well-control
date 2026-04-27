from rest_framework import serializers
from .models import Well, TelemetryData, Alert, CommandLog


class WellSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Well.
    Преобразует объекты модели Well в JSON и обратно.
    Включает все поля модели для чтения и записи.
    """
    class Meta:
        model = Well
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate_depth(self, value):
        """
        Валидация глубины скважины.
        Args:
            value: Значение глубины
        Returns:
            float: Проверенное значение
        Raises:
            serializers.ValidationError: Если глубина некорректна
        """
        if value <= 0:
            raise serializers.ValidationError("Глубина скважины должна быть положительным числом")
        if value > 10000:
            raise serializers.ValidationError("Глубина скважины не может превышать 10 000 метров")
        return value

    def validate_diameter(self, value):
        """
        Валидация диаметра колонны.
        Args:
            value: Значение диаметра
        Returns:
            float: Проверенное значение
        """
        if value <= 0:
            raise serializers.ValidationError("Диаметр колонны должен быть положительным числом")
        if value > 1000:
            raise serializers.ValidationError("Диаметр колонны не может превышать 1000 мм")
        return value

    def to_representation(self, instance):
        """
        Кастомизация вывода JSON.
        Args:
            instance: Объект модели Well
        Returns:
            dict: Словарь с данными для JSON
        """
        representation = super().to_representation(instance)
        # Добавляем единицы измерения для наглядности
        representation['depth'] = f"{representation['depth']} м"
        representation['diameter'] = f"{representation['diameter']} мм"
        representation['pump_depth'] = f"{representation['pump_depth']} м"
        representation['dynamic_level'] = f"{representation['dynamic_level']} м"
        representation['static_level'] = f"{representation['static_level']} м"
        representation['formation_debit'] = f"{representation['formation_debit']} м³/сут"
        return representation


class WellListSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для модели Well
    Преобразует объекты модели Well в JSON и обратно.
    Используется при выводе списка для уменьшения объема данных.
    Включает только ключевые параметры.
    """
    class Meta:
        model = Well
        fields = ('id', 'name', 'depth', 'pump_depth', 'formation_debit', 'is_active')

    def to_representation(self, instance):
        """
        Кастомизация вывода JSON.
        Args:
            instance: Объект модели Well
        Returns:
            dict: Словарь с данными для JSON
        """
        representation = super().to_representation(instance)
        # Добавляем единицы измерения для наглядности
        representation['depth'] = f"{representation['depth']} м"
        representation['pump_depth'] = f"{representation['pump_depth']} м"
        representation['formation_debit'] = f"{representation['formation_debit']} м³/сут"
        return representation


class WellDetailSerializer(serializers.ModelSerializer):
    """
    Расширенный сериализатор для детального просмотра скважины
    с автоматически рассчитанными параметрами
    """
    # Расчетные поля (не хранятся в БД)
    calculated_max_flow = serializers.SerializerMethodField()
    calculated_recommended_flow = serializers.SerializerMethodField()
    calculated_pump_depth = serializers.SerializerMethodField()
    calculated_required_head = serializers.SerializerMethodField()
    mixture_density = serializers.SerializerMethodField()
    min_intake_pressure = serializers.SerializerMethodField()

    class Meta:
        model = Well
        fields = [
            # Все поля модели
            'id', 'name', 'external_id', 'is_active',
            'depth', 'reservoir_pressure', 'productivity_index',
            'oil_density', 'water_density', 'gas_factor', 'water_cut',
            'bubble_point_pressure', 'oil_volume_factor',
            'casing_inner_diameter', 'nkt_diameter', 'nkt_wall_thickness',
            'buffer_pressure', 'formation_debit', 'pump_depth',
            'created_at', 'updated_at',
            # Расчетные поля
            'calculated_max_flow',
            'calculated_recommended_flow',
            'calculated_pump_depth',
            'calculated_required_head',
            'mixture_density',
            'min_intake_pressure'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def get_calculated_max_flow(self, obj):
        """Максимально возможный дебит"""
        return obj.get_max_possible_flow()

    def get_calculated_recommended_flow(self, obj):
        """Рекомендуемый дебит"""
        return obj.get_recommended_flow()

    def get_calculated_pump_depth(self, obj):
        """Глубина спуска насоса"""
        flow = self.context.get('target_flow') if hasattr(self, 'context') else None
        return obj.get_pump_depth(flow)

    def get_calculated_required_head(self, obj):
        """Рекомендуемый напор насоса"""
        flow = self.context.get('target_flow') if hasattr(self, 'context') else None
        return obj.calculate_required_head(flow)

    def get_mixture_density(self, obj):
        """Плотность смеси нефть+вода"""
        return obj.get_mixture_density()

    def get_min_intake_pressure(self, obj):
        """Минимальное давление на приеме насоса"""
        return obj.get_min_intake_pressure()



class TelemetrySerializer(serializers.ModelSerializer):
    """
    Serializer for TelemetryData model.
    """

    well_name = serializers.CharField(source='well.name', read_only=True)
    current_unbalance = serializers.SerializerMethodField()

    class Meta:
        model = TelemetryData
        fields = '__all__'
        # exclude = ('raw_data',)
        read_only_fields = ('created_at',)

    def get_current_unbalance(self, obj):
        """
        Get current unbalance value.
        """
        return obj.current_unbalance()


from rest_framework import serializers
from .models import TelemetryData


class AlertSerializer(serializers.ModelSerializer):
    well_name = serializers.CharField(source='well.name', read_only=True)

    class Meta:
        model = Alert
        fields = '__all__'


class CommandLogSerializer(serializers.ModelSerializer):
    well_name = serializers.CharField(source='well.name', read_only=True)

    class Meta:
        model = CommandLog
        fields = '__all__'
