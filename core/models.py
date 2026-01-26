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


class ElectricMotor(models.Model):
    """
    Модель электродвигателя для ЭЦН.

    Хранит технические характеристики электродвигателя
    согласно ГОСТ и техническому заданию (Таблица A.1).
    """
    # Основная информация
    motor_type = models.CharField(
        max_length=100,
        verbose_name="Тип двигателя",
        help_text="Тип по ГОСТ (например, ЭД(T)16-103M1)"
    )
    manufacturer = models.CharField(
        max_length=150,
        default="Русэлпром",
        verbose_name="Производитель",
        help_text="Компания-производитель"
    )

    # Электрические параметры (из таблицы A.1)
    nominal_power = models.FloatField(
        verbose_name="Номинальная мощность",
        help_text="Мощность двигателя, кВт (столбец 2)"
    )
    nominal_voltage = models.FloatField(
        verbose_name="Номинальное напряжение",
        help_text="Рабочее напряжение, В (столбец 3)"
    )
    nominal_current = models.FloatField(
        verbose_name="Номинальный ток",
        help_text="Рабочий ток, А (столбец 4)"
    )
    efficiency = models.FloatField(
        verbose_name="КПД",
        help_text="Коэффициент полезного действия, % (столбец 5)"
    )
    power_factor = models.FloatField(
        verbose_name="Коэффициент мощности",
        help_text="Cos φ номинальный (столбец 6)"
    )
    nominal_slip = models.FloatField(
        verbose_name="Номинальное скольжение",
        help_text="Скольжение двигателя, % (столбец 7)"
    )

    # Механические параметры (из таблицы A.1)
    min_well_diameter = models.FloatField(
        verbose_name="Минимальный диаметр скважин",
        help_text="Минимальный диаметр скважины для монтажа, мм (столбец 8)"
    )
    coolant_velocity = models.FloatField(
        verbose_name="Скорость охлаждающей жидкости",
        help_text="Минимальная скорость охлаждающей жидкости, м/с (столбец 9)"
    )
    shaft_torque = models.FloatField(
        verbose_name="Момент проворачивания вала",
        help_text="Момент проворачивания при (20±5)°С, кгс·м (столбец 10)"
    )
    insulation_resistance = models.FloatField(
        verbose_name="Сопротивление изоляции обмотки",
        help_text="Сопротивление изоляции при 115°C, МОм (столбец 11)"
    )

    # Дополнительные параметры (из общего ТЗ)
    insulation_class = models.CharField(
        max_length=50,
        default="F",
        verbose_name="Класс изоляции",
        help_text="Класс изоляции обмоток (F, H и т.д.)"
    )
    protection_class = models.CharField(
        max_length=50,
        default="IP54",
        verbose_name="Степень защиты",
        help_text="Степень защиты IP (IP54, IP55 и т.д.)"
    )
    weight = models.FloatField(
        verbose_name="Масса",
        help_text="Масса двигателя, кг"
    )
    dimensions = models.CharField(
        max_length=200,
        default="Ø103 мм",
        verbose_name="Габариты",
        help_text="Габаритные размеры"
    )

    # Технические характеристики
    sections_count = models.IntegerField(
        default=1,
        verbose_name="Количество секций",
        help_text="Количество секций двигателя (1-3)"
    )
    operating_temperature = models.FloatField(
        default=90.0,
        verbose_name="Рабочая температура",
        help_text="Максимальная рабочая температура, °C"
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Двигатель доступен для использования"
    )

    def __str__(self):
        """Строковое представление двигателя."""
        return f"{self.motor_type} - {self.nominal_power} кВт"

    class Meta:
        """Метаданные модели."""
        verbose_name = "Электродвигатель"
        verbose_name_plural = "Электродвигатели"
        ordering = ['nominal_power', 'motor_type']
        unique_together = ['motor_type', 'nominal_power']

    def calculate_power_consumption(self, operating_hours=24):
        """
        Расчет потребления электроэнергии.

        Args:
            operating_hours: Часы работы в сутки

        Returns:
            float: Потребление электроэнергии, кВт·ч/сутки
        """
        # P = √3 × U × I × cosφ
        apparent_power = 1.732 * self.nominal_voltage * self.nominal_current * self.power_factor / 1000
        return apparent_power * operating_hours

    def get_cooling_requirement(self):
        """
        Требования к охлаждению двигателя.

        Returns:
            dict: Параметры охлаждения
        """
        return {
            'min_velocity': self.coolant_velocity,
            'min_flow_rate': self.coolant_velocity * 3.14 * (0.103 / 2) ** 2 * 3600,  # м³/ч
            'well_diameter_limit': self.min_well_diameter
        }



class PumpCharacteristic(models.Model):
    """
    Модель для хранения полиномиальных характеристик насосов ЭЦН.

    Хранит экспериментальные данные Q-H, Q-N, Q-η характеристик
    из Excel файлов производителя. Объединяет в себе как характеристики,
    так и основные технические параметры насоса.
    """
    # Идентификационные данные из Excel
    cod = models.IntegerField(
        verbose_name="Код насоса",
        help_text="Код из колонки 'cod' Excel файла"
    )
    zavod = models.CharField(
        max_length=50,
        default="ESP",
        verbose_name="Завод",
        help_text="Завод-изготовитель из колонки 'Zavod'"
    )
    harka_stupen = models.CharField(
        max_length=100,
        verbose_name="Марка ступени",
        help_text="Марка ступени из колонки 'harka_stupen' (например, ТД1750-200)"
    )
    material_stupen = models.CharField(
        max_length=100,
        verbose_name="Материал ступени",
        help_text="Материал ступени из колонки 'material_stupen'"
    )

    # Характеристики (храним как JSON)
    q_values = models.JSONField(
        verbose_name="Значения подачи (Q)",
        help_text="Массив значений подачи, м³/сут (колонка Q)",
        default=list
    )
    h_values = models.JSONField(
        verbose_name="Значения напора (H)",
        help_text="Массив значений напора, м (колонка H)",
        default=list
    )
    n_values = models.JSONField(
        verbose_name="Значения мощности (N)",
        help_text="Массив значений мощности, кВт (колонка N)",
        default=list
    )
    kpd_values = models.JSONField(
        verbose_name="Значения КПД (η)",
        help_text="Массив значений КПД, % (колонка KPD)",
        default=list
    )

    # Рабочие диапазоны из Excel
    left_range = models.FloatField(
        verbose_name="Левая граница",
        help_text="Левая граница рабочего диапазона (колонка Left)"
    )
    nominal_range = models.FloatField(
        verbose_name="Номинальная подача",
        help_text="Номинальная подача (колонка Nominal)"
    )
    right_range = models.FloatField(
        verbose_name="Правая граница",
        help_text="Правая граница рабочего диапазона (колонка Right)"
    )

    # Минимальный КПД по Роснефти
    min_kpd_rosneft = models.FloatField(
        default=25.0,
        verbose_name="Минимальный КПД Роснефть",
        help_text="Минимальный допустимый КПД по стандартам Роснефти"
    )

    # Технические характеристики насоса (добавленные)
    nominal_head = models.FloatField(
        verbose_name="Номинальный напор",
        help_text="Напор при номинальной подаче, м",
        null=True,
        blank=True
    )

    stages_count = models.IntegerField(
        verbose_name="Количество ступеней",
        help_text="Количество рабочих ступеней",
        null=True,
        blank=True
    )

    housing_diameter = models.FloatField(
        verbose_name="Диаметр корпуса",
        help_text="Наружный диаметр, мм",
        default=103.0
    )

    flow_part_material = models.CharField(
        max_length=100,
        default="Нерезист",
        verbose_name="Материал проточной части",
        help_text="Материал рабочих колес и направляющих аппаратов"
    )

    # Оптимальный диапазон (вычисляется автоматически)
    optimal_flow_range = models.JSONField(
        verbose_name="Оптимальный диапазон работы",
        help_text="Диапазон оптимальной работы [min, max], м³/сут",
        default=list
    )

    max_efficiency = models.FloatField(
        verbose_name="Максимальный КПД",
        help_text="Максимальное значение КПД, %",
        null=True,
        blank=True
    )

    max_efficiency_flow = models.FloatField(
        verbose_name="Подача при максимальном КПД",
        help_text="Подача при максимальном КПД, м³/сут",
        null=True,
        blank=True
    )

    # Метаданные
    source_file = models.CharField(
        max_length=255,
        verbose_name="Исходный файл",
        help_text="Имя файла Excel с исходными данными"
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Строковое представление характеристики."""
        return f"{self.harka_stupen} (код: {self.cod}, Qном: {self.nominal_range} м³/сут)"

    class Meta:
        """Метаданные модели."""
        verbose_name = "Насос ЭЦН"
        verbose_name_plural = "Насосы ЭЦН"
        ordering = ['cod', 'harka_stupen']
        unique_together = ['cod', 'harka_stupen', 'source_file']

    def save(self, *args, **kwargs):
        """
        Автоматический расчет при сохранении.
        """
        # 1. Вычисляем точку максимального КПД (ДОЛЖНО БЫТЬ ПЕРВЫМ)
        if self.kpd_values and self.q_values:
            # Находим максимальный КПД
            max_kpd = max(self.kpd_values)
            max_idx = self.kpd_values.index(max_kpd)

            self.max_efficiency = max_kpd
            self.max_efficiency_flow = self.q_values[max_idx]

            # 2. Вычисляем оптимальный диапазон (75% от максимального КПД)
            if max_kpd > 0:
                threshold_kpd = max_kpd * 0.75

                # Находим диапазон где КПД ≥ 75% от максимального
                start_idx = None
                end_idx = None

                # Ищем левую границу (идем от максимума влево)
                for i in range(max_idx, -1, -1):
                    if self.kpd_values[i] >= threshold_kpd:
                        start_idx = i
                    else:
                        break  # КПД упал ниже порога

                # Ищем правую границу (идем от максимума вправо)
                for i in range(max_idx, len(self.kpd_values)):
                    if self.kpd_values[i] >= threshold_kpd:
                        end_idx = i
                    else:
                        break  # КПД упал ниже порога

                if start_idx is not None and end_idx is not None:
                    self.optimal_flow_range = [
                        self.q_values[start_idx],
                        self.q_values[end_idx]
                    ]
                else:
                    # Если не нашли диапазон, используем рабочий
                    self.optimal_flow_range = [
                        self.left_range,
                        self.right_range
                    ]
            else:
                # Если нет КПД, используем рабочий диапазон
                self.optimal_flow_range = [
                    self.left_range,
                    self.right_range
                ]
        else:
            # Если нет данных, сбрасываем
            self.max_efficiency = None
            self.max_efficiency_flow = None
            self.optimal_flow_range = []

        # 3. Вычисляем номинальный напор
        if (not self.nominal_head and
                self.nominal_range and
                self.q_values and
                self.h_values):
            try:
                idx = min(range(len(self.q_values)),
                          key=lambda i: abs(self.q_values[i] - self.nominal_range))
                self.nominal_head = self.h_values[idx]
            except:
                pass

        # 4. Извлекаем количество ступеней из названия
        if not self.stages_count and self.harka_stupen:
            try:
                parts = self.harka_stupen.split('-')
                if len(parts) > 0:
                    num_part = parts[0].replace('ТД', '')
                    self.stages_count = int(num_part)
            except:
                pass

        super().save(*args, **kwargs)
    def calculate_at_point(self, q_value):
        """
        Расчет параметров в заданной точке подачи.

        Args:
            q_value: Подача, м³/сут

        Returns:
            dict: Параметры насоса
        """
        h = self._interpolate(self.q_values, self.h_values, q_value)
        n = self._interpolate(self.q_values, self.n_values, q_value)
        kpd = self._interpolate(self.q_values, self.kpd_values, q_value)

        return {
            'q': q_value,
            'h': h,
            'n': n,
            'kpd': kpd,
            'is_in_working_range': self.left_range <= q_value <= self.right_range,
            'is_optimal': (
                    self.optimal_flow_range and
                    self.optimal_flow_range[0] <= q_value <= self.optimal_flow_range[1]
            ),
            'head_at_nominal': self.nominal_head,
            'stages_count': self.stages_count
        }

    def get_qh_curve(self):
        """
        Получение данных для кривой Q-H.

        Returns:
            dict: Данные для графика
        """
        return {
            'x': self.q_values,
            'y': self.h_values,
            'name': f"{self.harka_stupen} (Q-H)",
            'nominal_point': {
                'x': self.nominal_range,
                'y': self.nominal_head
            } if self.nominal_head else None,
            'working_range': [self.left_range, self.right_range],
            'optimal_range': self.optimal_flow_range
        }

    def get_efficiency_curve(self):
        """
        Получение данных для кривой КПД.

        Returns:
            dict: Данные для графика
        """
        return {
            'x': self.q_values,
            'y': self.kpd_values,
            'name': f"{self.harka_stupen} (КПД)",
            'min_kpd_line': self.min_kpd_rosneft,
            'optimal_range': self.optimal_flow_range,
            'working_range': [self.left_range, self.right_range],
            'max_efficiency': max(self.kpd_values) if self.kpd_values else 0
        }

    def calculate_power_consumption(self, q_value=None, fluid_density=850.0):
        """
        Расчет потребляемой мощности.

        Args:
            q_value: Подача (если None - используем номинальную)
            fluid_density: Плотность жидкости, кг/м³

        Returns:
            dict: Результаты расчета
        """
        if q_value is None:
            q_value = self.nominal_range

        params = self.calculate_at_point(q_value)

        # Гидравлическая мощность: Nг = ρ * g * Q * H / (3600 * 1000)
        hydraulic_power = (fluid_density * 9.81 * params['q'] * params['h']) / (3600 * 1000)

        # Потребляемая мощность из характеристики
        shaft_power = params['n']

        return {
            'flow_rate': params['q'],
            'head': params['h'],
            'hydraulic_power_kw': round(hydraulic_power, 2),
            'shaft_power_kw': shaft_power,
            'efficiency_percent': params['kpd'],
            'calculated_efficiency': round((hydraulic_power / shaft_power * 100), 2) if shaft_power > 0 else 0
        }

    def find_best_efficiency_point(self):
        """
        Нахождение точки максимального КПД.

        Returns:
            dict: Параметры точки максимального КПД
        """
        if not self.kpd_values:
            return None

        max_kpd = max(self.kpd_values)
        max_idx = self.kpd_values.index(max_kpd)

        return {
            'q': self.q_values[max_idx],
            'h': self.h_values[max_idx],
            'n': self.n_values[max_idx],
            'kpd': max_kpd,
            'index': max_idx
        }

    def _interpolate(self, x_values, y_values, x):
        """
        Линейная интерполяция.
        """
        if not x_values or not y_values:
            return 0

        if x <= x_values[0]:
            return y_values[0]
        if x >= x_values[-1]:
            return y_values[-1]

        for i in range(len(x_values) - 1):
            if x_values[i] <= x <= x_values[i + 1]:
                x1, x2 = x_values[i], x_values[i + 1]
                y1, y2 = y_values[i], y_values[i + 1]
                return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
        return 0
