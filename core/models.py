from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator  # добавить эту строку
import math


class Well(models.Model):
    """
    Нефтяная скважина
    Хранит геологические и эксплуатационные параметры скважины
    """

    # --- ОСНОВНАЯ ИНФОРМАЦИЯ (обязательная) ---
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название скважины",
        help_text="Уникальное название скважины"
    )

    external_id = models.CharField(
        max_length=100,
        verbose_name="ID во внешней системе",
        help_text="Идентификатор скважины во внешнем API",
        blank=True,
        null=True,
        unique=True
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
        help_text="Скважина находится в эксплуатации"
    )

    # --- ГЕОЛОГИЧЕСКИЕ ПАРАМЕТРЫ (обязательные для расчетов) ---
    depth = models.FloatField(
        verbose_name="Глубина скважины",
        help_text="Глубина до забоя (кровли пласта), м"
    )

    reservoir_pressure = models.FloatField(
        verbose_name="Пластовое давление",
        help_text="Давление в продуктивном пласте, МПа"
    )

    productivity_index = models.FloatField(
        verbose_name="Коэффициент продуктивности",
        help_text="K_прод, м³/сут·МПа"
    )

    casing_inner_diameter = models.FloatField(
        verbose_name="Внутренний диаметр эксплуатационной колонны",
        help_text="Внутренний диаметр обсадной колонны, мм"
    )

    # --- ПАРАМЕТРЫ ЖИДКОСТИ (обязательные) ---
    oil_density = models.FloatField(
        verbose_name="Плотность нефти",
        help_text="Плотность сепарированной нефти в поверхностных условиях, кг/м³",
        default=850.0
    )

    water_density = models.FloatField(
        verbose_name="Плотность воды",
        help_text="Плотность пластовой воды, кг/м³",
        default=1170.0
    )

    gas_factor = models.FloatField(
        verbose_name="Газовый фактор",
        help_text="Газосодержание, м³/т",
        default=50.0
    )

    water_cut = models.FloatField(
        verbose_name="Обводненность",
        help_text="Объемная доля воды в продукции, %",
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # --- ПАРАМЕТРЫ ЖИДКОСТИ (опциональные, для точных расчетов) ---
    bubble_point_pressure = models.FloatField(
        verbose_name="Давление насыщения",
        help_text="Давление насыщения нефти газом, МПа",
        null=True,
        blank=True
    )

    oil_volume_factor = models.FloatField(
        verbose_name="Объемный коэффициент нефти",
        help_text="Объемный коэффициент нефти при давлении насыщения",
        default=1.1
    )

    # --- КОНСТРУКЦИЯ СКВАЖИНЫ (опциональные, есть значения по умолчанию) ---
    nkt_diameter = models.FloatField(
        verbose_name="Наружный диаметр НКТ",
        help_text="Наружный диаметр насосно-компрессорных труб, мм",
        default=73.0
    )

    nkt_wall_thickness = models.FloatField(
        verbose_name="Толщина стенки НКТ",
        help_text="Толщина стенки насосно-компрессорных труб, мм",
        default=5.5
    )

    buffer_pressure = models.FloatField(
        verbose_name="Буферное давление",
        help_text="Давление на устье скважины, МПа",
        default=1.0
    )

    # --- ЭКСПЛУАТАЦИОННЫЕ ПАРАМЕТРЫ (опциональные) ---
    formation_debit = models.FloatField(
        verbose_name="Пластовый дебит",
        help_text="Плановый или фактический дебит скважины, м³/сут",
        null=True,
        blank=True
    )

    pump_depth = models.FloatField(
        verbose_name="Глубина спуска насоса",
        help_text="Глубина установки насоса, м. Если не указана - рассчитывается автоматически",
        null=True,
        blank=True
    )

    # --- СИСТЕМНЫЕ ПОЛЯ ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Скважина"
        verbose_name_plural = "Скважины"
        ordering = ['name']

    def __str__(self):
        return self.name

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ РАСЧЕТОВ =====

    def _get_nkt_inner_diameter(self):
        """Внутренний диаметр НКТ, м"""
        return (self.nkt_diameter - 2 * self.nkt_wall_thickness) / 1000

    def _get_casing_inner_diameter_m(self):
        """Внутренний диаметр эксплуатационной колонны, м"""
        return self.casing_inner_diameter / 1000

    def _get_annular_area(self):
        """Площадь межтрубного пространства, м²"""
        D_cas = self._get_casing_inner_diameter_m()
        d_nkt = self._get_nkt_inner_diameter()
        return (math.pi / 4) * (D_cas**2 - d_nkt**2)

    def _get_motor_annular_area(self):
        """Площадь сечения вокруг ПЭД, м²"""
        D_cas = self._get_casing_inner_diameter_m()
        motor_diameter = 0.117  # стандартный диаметр ПЭД, м
        return (math.pi / 4) * (D_cas**2 - motor_diameter**2)

    def get_mixture_density(self, water_cut=None):
        """
        Плотность смеси без учета газа, кг/м³
        Если water_cut не указан, используется значение из модели
        """
        wcut = water_cut if water_cut is not None else self.water_cut
        oil_fraction = 1 - wcut / 100
        water_fraction = wcut / 100
        return self.oil_density * oil_fraction + self.water_density * water_fraction

    def get_max_possible_flow(self):
        """
        Максимально возможный дебит по коэффициенту продуктивности, м³/сут
        """
        if self.productivity_index and self.reservoir_pressure:
            P_zab_min = 5.0  # минимальное забойное давление, МПа
            return self.productivity_index * (self.reservoir_pressure - P_zab_min)
        return None

    def get_recommended_flow(self):
        """
        Рекомендуемый дебит (не больше formation_debit если он задан)
        """
        max_flow = self.get_max_possible_flow()

        if max_flow:
            recommended = max_flow * 0.8
        else:
            recommended = 100

        # Если задан formation_debit, не превышаем его
        if self.formation_debit:
            return min(recommended, self.formation_debit)

        return recommended

    def get_min_intake_pressure(self):
        """
        Минимальное давление на приеме насоса, МПа
        """
        if self.bubble_point_pressure:
            return 0.75 * self.bubble_point_pressure  # 25% свободного газа
        return 3.0  # значение по умолчанию

    def get_fluid_properties_at_intake(self, flow_rate, intake_pressure):
        """
        Расчет свойств жидкости на приеме насоса

        Args:
            flow_rate: Дебит жидкости, м³/сут
            intake_pressure: Давление на приеме насоса, МПа

        Returns:
            dict: Свойства жидкости на приеме
        """
        # Объемный коэффициент при текущем давлении
        if self.bubble_point_pressure and intake_pressure >= self.bubble_point_pressure:
            B = self.oil_volume_factor
            gas_fraction = 0
        elif self.bubble_point_pressure:
            # Формула 8.7 из стандарта
            B = self.water_cut/100 + (1 - self.water_cut/100) * (
                1 + (self.oil_volume_factor - 1) * (intake_pressure / self.bubble_point_pressure)**0.5
            )

            # Объемное газосодержание (формула 8.10)
            gas_fraction = 1 / (
                (1 + intake_pressure) * B + 1 / (
                    self.gas_factor * (1 - intake_pressure / self.bubble_point_pressure)
                )
            )
        else:
            B = 1.0
            gas_fraction = 0

        # Расход на приеме, м³/с
        flow_at_intake = flow_rate * B / 86400

        # Плотность смеси на приеме
        if gas_fraction > 0:
            rho_liquid = self.get_mixture_density()
            rho_gas = 1.2 * (intake_pressure / 0.1)  # приближенно
            rho_mix = rho_liquid * (1 - gas_fraction) + rho_gas * gas_fraction
        else:
            rho_mix = self.get_mixture_density()

        return {
            'flow_at_intake': flow_at_intake,
            'gas_fraction': gas_fraction,
            'density': rho_mix,
            'volume_factor': B
        }

    def get_pump_depth(self, target_flow=None, intake_pressure=None):
        """
        Возвращает глубину спуска насоса.
        Если пользователь указал - возвращает её.
        Если нет - рассчитывает автоматически.
        """
        # Если пользователь указал глубину - используем её
        if self.pump_depth is not None:
            return self.pump_depth

        # Иначе рассчитываем автоматически
        g = 9.81

        if target_flow is None:
            target_flow = self.get_recommended_flow()

        # Забойное давление при заданном дебите
        if self.productivity_index and self.reservoir_pressure:
            P_zab = self.reservoir_pressure - target_flow / self.productivity_index
        else:
            P_zab = self.reservoir_pressure * 0.7 if self.reservoir_pressure else 10.0

        # Динамический уровень
        rho = self.get_mixture_density()
        H_din = self.depth - (P_zab * 1e6) / (rho * g)

        # Давление на приеме
        if intake_pressure is None:
            P_intake = self.get_min_intake_pressure()
        else:
            P_intake = intake_pressure

        # Глубина спуска насоса
        calculated_depth = H_din + (P_intake * 1e6) / (rho * g)

        return round(calculated_depth, 1)

    def calculate_required_head(self, flow_rate, intake_pressure=None):
        """
        Расчет потребного напора насоса для заданного дебита

        Args:
            flow_rate: Планируемый дебит, м³/сут
            intake_pressure: Давление на приеме (если None - рассчитывается)

        Returns:
            float: Потребный напор насоса, м
        """
        g = 9.81

        # Забойное давление при заданном дебите
        if self.productivity_index and self.reservoir_pressure:
            P_zab = self.reservoir_pressure - flow_rate / self.productivity_index
        else:
            P_zab = self.reservoir_pressure * 0.7 if self.reservoir_pressure else 10.0

        # Давление на приеме насоса
        if intake_pressure is None:
            P_intake = self.get_min_intake_pressure()
        else:
            P_intake = intake_pressure

        # Свойства жидкости на приеме
        props = self.get_fluid_properties_at_intake(flow_rate, P_intake)

        # Динамический уровень
        H_din = self.depth - (P_zab * 1e6) / (props['density'] * g)

        # Глубина спуска насоса
        L_pump = H_din + (P_intake * 1e6) / (props['density'] * g)

        # Скорость жидкости в НКТ
        d_inner = self._get_nkt_inner_diameter()
        nkt_area = math.pi * d_inner**2 / 4
        velocity = flow_rate / (86400 * nkt_area)

        # Потери на трение
        Re = velocity * d_inner / 1e-6  # число Рейнольдса
        if Re < 2300:
            lambda_coef = 64 / Re
        else:
            lambda_coef = 0.3164 / Re**0.25

        h_tr = lambda_coef * (L_pump / d_inner) * (velocity**2 / (2*g))

        # Буферное давление в метрах
        h_buf = (self.buffer_pressure * 1e6) / (props['density'] * g)

        # Газлифтный эффект
        if props['gas_fraction'] > 0 and self.bubble_point_pressure:
            C_slip = 2e-4 if self.water_cut < 50 else 16e-4
            phi = props['gas_fraction'] / (1 + C_slip * props['flow_at_intake'] / self._get_annular_area())
            P_gas = self.bubble_point_pressure * (1 / (1 - 0.4*phi) - 1)
            h_gas = (P_gas * 1e6) / (props['density'] * g)
        else:
            h_gas = 0

        # ИТОГО: потребный напор
        required_head = L_pump + h_buf + h_tr - h_gas

        print(f"DEBUG: L_pump={L_pump:.0f} м, h_buf={h_buf:.0f} м, h_tr={h_tr:.0f} м, h_gas={h_gas:.0f} м")
        print(f"DEBUG: required_head={required_head:.0f} м")

        return round(required_head, 1)


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

    recommended_motor = models.ForeignKey(
        'ElectricMotor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suitable_pump',
        verbose_name='Рекомендуемый двигатель',
        help_text='Электродвигатель, рекомендуемый для этого насоса'
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
            threshold_kpd = max_kpd * 0.75
            self.optimal_flow_range = []

            for i in range(len(self.q_values) - 1):
                k1, k2 = self.kpd_values[i], self.kpd_values[i + 1]
                q1, q2 = self.q_values[i], self.q_values[i + 1]

                # Проверяем, пересекает ли линия threshold_kpd на этом интервале
                if (k1 - threshold_kpd) * (k2 - threshold_kpd) <= 0:
                    # Линейная интерполяция
                    q = q1 + (q2 - q1) * (threshold_kpd - k1) / (k2 - k1)
                    self.optimal_flow_range.append(q)

            # if max_kpd > 0:
            #     threshold_kpd = max_kpd * 0.75

                # Находим диапазон где КПД ≥ 75% от максимального
                # start_idx = None
                # end_idx = None

                # # Ищем левую границу (идем от максимума влево)
                # for i in range(max_idx, -1, -1):
                #     if self.kpd_values[i] >= threshold_kpd:
                #         start_idx = i
                #     else:
                #         break  # КПД упал ниже порога
                #
                # # Ищем правую границу (идем от максимума вправо)
                # for i in range(max_idx, len(self.kpd_values)):
                #     if self.kpd_values[i] >= threshold_kpd:
                #         end_idx = i
                #     else:
                #         break  # КПД упал ниже порога

                # if start_idx is not None and end_idx is not None:
                #     self.optimal_flow_range = [
                #         self.q_values[start_idx],
                #         self.q_values[end_idx]
                #     ]
                # else:
                #     # Если не нашли диапазон, используем рабочий
                #     self.optimal_flow_range = [
                #         self.left_range,
                #         self.right_range
                #     ]
            # else:
            #     # Если нет КПД, используем рабочий диапазон
            #     self.optimal_flow_range = [
            #         self.left_range,
            #         self.right_range
            #     ]
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

    def calculate_at_point(self, q):
        """
        Расчет параметров в заданной точке подачи.

        Args:
            q_value: Подача, м³/сут

        Returns:
            dict: Параметры насоса
        """
        h = self._interpolate(self.q_values, self.h_values, q)
        n = self._interpolate(self.q_values, self.n_values, q)
        kpd = self._interpolate(self.q_values, self.kpd_values, q)

        return {
            'q': q,
            'h': h,
            'n': n,
            'kpd': kpd,
            'is_in_working_range': self.left_range <= q <= self.right_range,
            'is_optimal': (
                    self.optimal_flow_range and
                    self.optimal_flow_range[0] <= q <= self.optimal_flow_range[1]
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

    def calculate_power_consumption(self, q=None, fluid_density=850.0):
        """
        Расчет потребляемой мощности.

        Args:
            q: Подача (если None - используем номинальную)
            fluid_density: Плотность жидкости, кг/м³

        Returns:
            dict: Результаты расчета
        """
        if q is None:
            q = self.nominal_range

        params = self.calculate_at_point(q)

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


class ElectricMotor(models.Model):
    """
    Модель электродвигателя ЭЦН по данным испытаний.

    Соответствует структуре Excel файла с параметрами двигателей.
    """
    # Основная информация
    motor_id = models.CharField(
        max_length=50,
        verbose_name='ID двигателя',
        help_text='Идентификатор из Excel',
        unique=True,
        default="unknown_id"
    )
    model = models.CharField(
        max_length=100,
        verbose_name='Модель',
        help_text='Модель двигателя (Model)',
        default="Unknown_Model"
    )
    manufacturer = models.CharField(
        max_length=150,
        verbose_name="Производитель",
        help_text="Manufactured",
        default="Неизвестно"
    )

    # Основные номинальные параметры
    nominal_power = models.FloatField(
        verbose_name='Номинальная мощность, кВт',
        help_text='Power_nom',
        default=0.0
    )
    nominal_voltage = models.FloatField(
        verbose_name='Номинальное напряжение, В',
        help_text='U_nom',
        default=0.0
    )
    nominal_current = models.FloatField(
        verbose_name='Номинальный ток, А',
        help_text='I_nom',
        default=0.0
    )
    rotation_speed = models.FloatField(
        verbose_name='Обороты, об/мин',
        help_text='Turning',
        default=0.0
    )
    slip = models.FloatField(
        verbose_name='Скольжение, %',
        help_text='S_load',
        default=0.0
    )
    power_factor = models.FloatField(
        verbose_name='Коэффициент мощности',
        help_text='Powerfactcor_load',
        default=0.0
    )
    efficiency = models.FloatField(
        verbose_name='КПД, %',
        help_text='Efficiency_load',
        default=0.0
    )
    torque = models.FloatField(
        verbose_name='Крутящий момент, кгс.см',
        help_text='TurningMoment',
        default=0.0
    )

    # Механические характеристики
    shaft_torque = models.FloatField(
        verbose_name='Момент проворачивания вала, кгс.м',
        help_text='BoringMoment',
        default=0.0
    )

    # Электрические характеристики
    acceleration_voltage = models.FloatField(
        verbose_name='Напряжение разгона, В',
        help_text='U_accel',
        default=0.0
    )

    # Холостой ход
    idle_current = models.FloatField(
        verbose_name='Ток холостого хода, А',
        help_text='I_Idling',
        default=0.0
    )
    idle_voltage = models.FloatField(
        verbose_name='Напряжение холостого хода, В',
        help_text='U_Idling',
        default=0.0
    )

    # Изоляция
    insulation_test_voltage = models.FloatField(
        verbose_name='Испытание изоляции обмотки относительно корпуса на электрическую прочность, В',
        help_text='U_InsulWinding',
        default=0.0
    )
    interturn_test_voltage  = models.FloatField(
        verbose_name='Испытание межвитковой изоляции на электрическую прочность, В',
        help_text='U_MinInsulWinding',
        default=0.0
    )
    insulation_resistance = models.FloatField(
        verbose_name='Сопротивление изоляции, В',
        help_text='R_Insul',
        default=0.0
    )
    cold_winding_resistance = models.FloatField(
        verbose_name='Сопротивление обмотки (20°C) МОм',
        help_text='R_ColdWinding',
        default=0.0
    )
    cold_winding_resistance_delta = models.FloatField(
        verbose_name='Изменение сопротивления обмотки',
        help_text='dR_ColdWinding',
        null=True,
        blank=True
    )

    # Динамические характеристики
    rundown_time = models.FloatField(
        verbose_name='Выбег, с',
        help_text='Time_Rundown',
        default=0.0
    )
    vibration_level = models.FloatField(
        verbose_name='Вибрация, мм/с',
        help_text='VibrLevel',
        default=0.0
    )

    # Потери
    idle_losses = models.FloatField(
        verbose_name='Потери холостого хода, кВт',
        help_text='P_h_h',
        default=0.0
    )
    heated_waste = models.FloatField(
        verbose_name='Потери в нагретом состоянии, кВт',
        help_text='P_HeatedWaste',
        default=0.0
    )

    # Параметры короткого замыкания
    short_circuit_current = models.FloatField(
        verbose_name='Ток короткого замыкания, А',
        help_text='I_k_z',
        default=0.0
    )
    short_circuit_voltage = models.FloatField(
        verbose_name='Напряжение короткого замыкания, В',
        help_text='U_k_z',
        default=0.0
    )
    short_circuit_power = models.FloatField(
        verbose_name='Мощность короткого замыкания, кВт',
        help_text='P_k_z',
        default=0.0
    )

    source_file = models.CharField(
        max_length=255,
        verbose_name="Исходный файл",
        help_text="Файл Excel с исходными данными",
        default=""
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Строковое представление двигателя."""
        manufacturer_display = self.manufacturer if hasattr(self, 'manufacturer') else "Не указан"
        return f"{self.model} - {self.nominal_power} кВт, {self.nominal_voltage} В ({manufacturer_display})"

    class Meta:
        verbose_name = 'Электродвигатель'
        verbose_name_plural = 'Электродвигатели'
        ordering = ['model', 'nominal_power']
        # Indexes в Django - это индексы базы данных, которые создаются для ускорения поиска и
        # фильтрации данных по определенным полям
        indexes = [
            models.Index(fields=['model']),
            models.Index(fields=['nominal_power']),
            models.Index(fields=['nominal_voltage'])
        ]

    def calculate_rated_torque(self):
        """
        Расчет номинального момента.

        Returns:
             float: Номинальный момент, Н·м
        """
        # M = (P * 9550) / n
        if self.rotation_speed > 0:
            return (self.nominal_power * 9550) / self.rotation_speed
        return 0

    def calculate_starting_current_ratio(self):
        """
        Расчет кратности пускового тока.

         Returns:
             float: I_пуск / I_ном
        """
        if self.nominal_current > 0:
            return self.short_circuit_current / self.nominal_current
        return 0

    def get_vibration_status(self):
        """
         Определение статуса вибрации.

         Returns:
             dict: Статус и рекомендации
        """
        level = self.vibration_level

        if level <= 4:
            status = 'Удовлетворительное'
            color = 'green'
            recommendation = 'В пределах нормы'
        else:
            status = "Критическое"
            color = "red"
            recommendation = "Требуется ремонт"

        return {
            'level': level,
            'status': status,
            'color': color,
            'recommendation': recommendation,
            'standard': 'ГОСТ ISO 10816'
        }

    def calculate_efficiency_class(self):
        """
        Определение класса энергоэффективности по ГОСТ.

        Returns:
             str: Класс IE
        """
        if self.efficiency >= 90:
            return 'IE3 (Высокий)'
        elif self.efficiency >= 85:
            return 'IE2 (Стандартный)'
        elif self.efficiency >= 80:
            return 'IE1 (Базовый)'
        else:
            return 'Ниже стандарта'

    def calculate_power_consumption(self, operating_hours=24):
        """
        Расчет потребляемой электроэнергии.

        Agrs:
            operating_hours: Часы работы в сутки

        Returns:
             dict: Результаты расчета
        """
        # Активная мощность: P = √3 × U × I × cosφ
        apparent_power = 1.732 * self.nominal_voltage * self.nominal_current / 1000  # кВА
        active_power = apparent_power * self.power_factor  # кВт
        daily_consumption = active_power * operating_hours  # кВт·ч

        return {
            'apparent_power_kva': round(apparent_power, 2),
            'active_power_kw': round(active_power, 2),
            'daily_consumption_kwh': round(daily_consumption, 2),
            'monthly_consumption_kwh': round(daily_consumption * 30, 2),
            'power_factor': self.power_factor
        }

    def get_technical_summary(self):
        """
        Сводка технических характеристик.

        Returns:
             dict: Сводная информация
        """
        return {
            'identification': {
                'model': self.model,
                'manufacturer': self.manufacturer,
                'id': self.motor_id
            },
            'electrical': {
                'power': f"{self.nominal_power} кВт",
                'voltage': f"{self.nominal_voltage} В",
                'current': f"{self.nominal_current} А",
                'efficiency': f"{self.efficiency}%",
                'power_factor': self.power_factor
            },
            'mechanical': {
                'speed': f"{self.rotation_speed} об/мин",
                'torque': f"{self.torque} кгс.см",
                'shaft_torque': f"{self.shaft_torque} кгс.м",
                'vibration': f"{self.vibration_level} мм/с"
            },
            'insulation': {
                'resistance': f"{self.insulation_resistance} МОм",
                'test_voltage': f"{self.insulation_test_voltage} В"
            }
        }


class TelemetryData(models.Model):
    """
    Телеметрия скважины в реальном времени.

    Хранит параметры телеметрии в соответствии с разделом 3.1
    технической спецификации.
    """

    well = models.ForeignKey(
        Well,
        on_delete=models.CASCADE,
        related_name='telemetry',
        verbose_name="Скважина"
    )

    external_id = models.CharField(
        max_length=100,
        verbose_name="Внешний ID",
        blank=True
    )

    timestamp = models.DateTimeField(
        verbose_name="Время измерения"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время создания записи"
    )

    # Электрические параметры (3.1.1)
    current_phase_a = models.FloatField(
        verbose_name="Ток фазы А, А",
        null=True,
        blank=True
    )

    current_phase_b = models.FloatField(
        verbose_name="Ток фазы B, А",
        null=True,
        blank=True
    )

    current_phase_c = models.FloatField(
        verbose_name="Ток фазы C, А",
        null=True,
        blank=True
    )

    max_current = models.FloatField(
        verbose_name="Максимальный ток фазы, А",
        null=True,
        blank=True
    )

    avg_voltage = models.FloatField(
        verbose_name="Среднее напряжение фазы, В",
        null=True,
        blank=True
    )

    active_power = models.FloatField(
        verbose_name="Активная мощность, кВт",
        null=True,
        blank=True
    )

    apparent_power = models.FloatField(
        verbose_name="Полная мощность, кВА",
        null=True,
        blank=True
    )

    power_factor = models.FloatField(
        verbose_name="Коэффициент мощности (cos φ)",
        null=True,
        blank=True
    )

    frequency = models.FloatField(
        verbose_name="Частота, Гц",
        null=True,
        blank=True
    )

    insulation_resistance = models.FloatField(
        verbose_name="Сопротивление изоляции, МОм",
        null=True,
        blank=True
    )

    # Механические параметры (3.1.2)
    intake_pressure = models.FloatField(
        verbose_name="Давление на приеме, атм",
        null=True,
        blank=True
    )

    intake_temperature = models.FloatField(
        verbose_name="Температура на приеме, °C",
        null=True,
        blank=True
    )

    motor_temperature = models.FloatField(
        verbose_name="Температура двигателя, °C",
        null=True,
        blank=True
    )

    vibration_x = models.FloatField(
        verbose_name="Вибрация по оси X, мм/с",
        null=True,
        blank=True
    )

    vibration_y = models.FloatField(
        verbose_name="Вибрация по оси Y, мм/с",
        null=True,
        blank=True
    )

    load_percent = models.FloatField(
        verbose_name="Нагрузка, %",
        null=True,
        blank=True
    )

    # Сырые данные API
    raw_data = models.JSONField(
        verbose_name="Сырые данные API",
        default=dict,
        blank=True
    )

    data_source = models.CharField(
        max_length=100,
        verbose_name="Источник данных",
        default="external_api"
    )

    class Meta:
        """Метаданные модели."""
        verbose_name = "Телеметрия"
        verbose_name_plural = "Телеметрия"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['well', '-timestamp']),
            models.Index(fields=['external_id']),
        ]
        unique_together = ['well', 'external_id', 'timestamp']

    def __str__(self):
        """Строковое представление."""
        return f"{self.well.name} - {self.timestamp}"

    def current_unbalance(self):
        """
        Рассчитать несимметрию токов.

        Returns:
            float: Процент несимметрии токов или None
        """
        currents = [self.current_phase_a, self.current_phase_b, self.current_phase_c]
        if None in currents:
            return None
        avg = sum(currents) / 3
        max_dev = max(abs(c - avg) for c in currents)
        return (max_dev / avg) * 100 if avg > 0 else 0


class Alert(models.Model):
    """Модель для уведомлений о превышении параметров."""

    ALERT_TYPES = [
        ('pressure', 'Давление'),
        ('temperature', 'Температура'),
        ('vibration', 'Вибрация'),
        ('current', 'Ток'),
        ('power', 'Мощность'),
    ]

    SEVERITY_LEVELS = [
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('critical', 'Критично'),
    ]

    well = models.ForeignKey(
        Well,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name="Скважина"
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        verbose_name="Тип уведомления"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='warning',
        verbose_name="Важность"
    )
    message = models.TextField(
        verbose_name="Сообщение"
    )
    value = models.FloatField(
        verbose_name="Значение",
        null=True,
        blank=True
    )
    threshold = models.FloatField(
        verbose_name="Порог",
        null=True,
        blank=True
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время"
    )

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.well.name} - {self.message}"


class CommandLog(models.Model):
    """
    Модель для аудита всех отправленных команд.
    """
    COMMAND_TYPES = [
        ('frequency_adjust', 'Изменение частоты'),
        ('start', 'Запуск'),
        ('stop', 'Остановка'),
        ('emergency_stop', 'Аварийная остановка'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Отправлено'),
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
    ]

    well = models.ForeignKey(
        Well,
        on_delete=models.CASCADE,
        related_name='command_logs',
        verbose_name="Скважина"
    )
    command_type = models.CharField(
        max_length=20,
        choices=COMMAND_TYPES,
        verbose_name="Тип команды"
    )
    parameters = models.JSONField(
        verbose_name="Параметры",
        default=dict
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name="Статус"
    )
    response = models.JSONField(
        verbose_name="Ответ внешней системы",
        null=True,
        blank=True
    )
    error_message = models.TextField(
        verbose_name="Сообщение об ошибке",
        blank=True
    )
    created_by = models.CharField(
        max_length=100,
        verbose_name="Инициатор",
        default="system"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог команды"
        verbose_name_plural = "Логи команд"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['well', '-created_at']),
            models.Index(fields=['command_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.well.name} - {self.get_command_type_display()} - {self.created_at}"
