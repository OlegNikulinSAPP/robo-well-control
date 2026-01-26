from rest_framework import serializers
from .models import Well


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