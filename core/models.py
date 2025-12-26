from django.db import models


class Well(models.Model):
    """
    Модель добывающей скважины.

    Хранит основные геологические и конструктивные параметры скважины
    согласно разделу 3.2 технического задания.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Номер скважины",
        help_text="Уникальный номер скважины (например, 'Скважина №1')"
    )
    depth = models.FloatField(
        verbose_name="Глубина скважины",
        help_text="Общая глубина скважины, метров"
    )
    diameter = models.FloatField(
        verbose_name="Диаметр колонны",
        help_text="Диаметр эксплуатационной колонны, миллиметров"
    )
    pump_depth = models.FloatField(
        verbose_name="Глубина спуска насоса",
        help_text="Глубина установки ЭЦН, метров"
    )
    dynamic_level = models.FloatField(
        verbose_name="Динамический уровень",
        help_text="Уровень жидкости при работе насоса, метров"
    )
    static_level = models.FloatField(
        verbose_name="Статический уровень",
        help_text="Уровень жидкости в покое, метров"
    )
    formation_debit = models.FloatField(
        verbose_name="Пластовый дебит",
        help_text="Расчетный дебит скважины, м³/сутки"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        help_text="Дата и время добавления скважины в систему"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
        help_text="Дата и время последнего обновления данных"
    )

    def __str__(self):
        """Строковое представление объекта для админки и отладки."""
        return f"{self.name} (глубина: {self.depth} м)"

    class Meta:
        """Метаданные модели."""
        verbose_name = "Скважина"
        verbose_name_plural = "Скважины"
        ordering = ['name']

