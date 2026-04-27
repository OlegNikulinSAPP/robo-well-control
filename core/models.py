from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime
import math
from functools import wraps


DEFAULT_PRESSURE_FRACTION = 0.7   # доля от пластового давления при отсутствии КП
MIN_BOTTOM_HOLE_PRESSURE = 12.0    # минимальное забойное давление, МПа
GRAVITY = 9.81                    # ускорение свободного падения, м/с2
SECONDS_IN_DAY = 86400
DEFAULT_FLOW = 100                # дебит по умолчанию
MIN_INTAKE_PRESSURE = 3           # минимальное значение давления на приеме насоса по умолчанию
MPA_TO_PA = 1e6                   # перевод мегапаскалей в паскали
WATER_KINEMATIC_VISCOSITY = 1e-6  # кинематическая вязкость воды, м²/с при 20°C


def with_defaults(func):
    """
    Декоратор для автоматической подстановки значений по умолчанию
    для параметров target_flow и intake_pressure.
    Если параметры не переданы или равны None, подставляются:
    - target_flow: результат get_recommended_flow()
    - intake_pressure: результат get_min_intake_pressure()
    """
    @wraps(func)
    def wrapper(self, target_flow=None, intake_pressure=None, **kwargs):
        flow = target_flow
        pressure = intake_pressure

        # Определяем target_flow
        if flow is None:
            flow = self.get_recommended_flow()

        # Определяем intake_pressure
        if pressure is None:
            pressure = self.get_min_intake_pressure()

        return func(self, target_flow=flow, intake_pressure=pressure, **kwargs)

    return wrapper


class Well(models.Model):
    """
    Нефтяная скважина.
    Хранит геологические и эксплуатационные параметры скважины
    """
    # --- Основная информация (обязательная) ---
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название (номер) скважины',
        help_text='Уникальное название (номер) скважины'
    )
    external_id = models.CharField(
        max_length=100,
        verbose_name='ID во внешней системе',
        help_text='Идентификатор скважины во внешнем API',
        blank=True,
        null=True,
        unique=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Скважина в эксплуатации',
        help_text='Скважина активна и участвует в добыче'
    )

    # --- ГЕОЛОГИЧЕСКИЕ ПАРАМЕТРЫ (обязательные для расчетов) ---
    depth = models.FloatField(
        verbose_name='Глубина скважины',
        help_text='Глубина до забоя (кровли пласта), м'
    )
    reservoir_pressure = models.FloatField(
        verbose_name='Пластовое давление',
        help_text='Давление в продуктивном пласте, МПа'
    )
    productivity_index = models.FloatField(
        verbose_name='Коэффициент продуктивности',
        help_text='K_прод, м3/сут*МПа'
    )
    casing_inner_diameter = models.FloatField(
        verbose_name='Внутренний диаметр эксплуатационной колонны',
        help_text='Внутренний диаметр обсадной колонны, мм'
    )

    # --- ПАРАМЕТРЫ ЖИДКОСТИ (обязательные) ---
    oil_density = models.FloatField(
        verbose_name='Плотность нефти',
        help_text='Плотность сепарированной нефти в поверхностных условиях, кг/м³',
        default=850.0
    )
    water_density = models.FloatField(
        verbose_name='Плотность воды',
        help_text='Плотность пластовой воды, кг/м³',
        default=1170.0
    )
    gas_factor = models.FloatField(
        verbose_name='Газовый фактор',
        help_text='Газосодержание м³/т',
        default=50.0
    )
    water_cut = models.FloatField(
        verbose_name='Обводненность',
        help_text='Объемная доля воды в продукции, %',
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # --- ПАРАМЕТРЫ ЖИДКОСТИ (опциональные, для точных расчетов) ---
    bubble_point_pressure = models.FloatField(
        verbose_name='Давление насыщения',
        help_text='Давление насыщения нефти газом, МПа',
        null=True,
        blank=True
    )
    oil_volume_factor = models.FloatField(
        verbose_name='Объемный коэффициент нефти',
        help_text='Объемный коэффициент нефти при давлении насыщения',
        default=1.1
    )

    # --- КОНСТРУКЦЯ СКВАЖИНЫ (опционально) ---
    nkt_diameter = models.FloatField(
        verbose_name='Наружный диаметр НКТ',
        help_text='Наружный диаметр насосно-компрессорных труб, мм',
        default=73.0
    )
    nkt_wall_thickness = models.FloatField(
        verbose_name='Толщина стенки НКТ',
        help_text='Толщина стенки насосно-компрессорных труб, мм',
        default=5.5
    )
    buffer_pressure = models.FloatField(
        verbose_name='Буферное давление',
        help_text='Давление на устье скважины, МПа',
        default=1.0
    )

    # --- ЭКСПЛУАТАЦИОННЫЕ ПАРАМЕТРЫ (опционально) ---
    formation_debit = models.FloatField(
        verbose_name='Пластовый дебит',
        help_text='Пластовый или фактический дебит скважины м3/сут',
        null=True,
        blank=True
    )
    pump_depth = models.FloatField(
        verbose_name='Глубина спуска насоса',
        help_text='Глубина установки насоса, м. Если не указана - рассчитывается автоматически',
        null=True,
        blank=True
    )

    # --- СИСТЕМНЫЕ ПОЛЯ ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Скважина'
        verbose_name_plural = 'Скважины'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def has_telemetry(self):
        return self.telemetry.exists()

    # ==== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ РАСЧЕТОВ ====
    def _get_nkt_inner_diameter(self):
        """Внутренний диаметр НКТ, м"""
        # Переводим мм в метры
        inner_diameter_mm = self.nkt_diameter - 2 * self.nkt_wall_thickness  # noqa
        return inner_diameter_mm / 1000

    def _get_casing_inner_diameter_m(self):
        """Внутренний диаметр эксплуатационной колонны, м"""
        return self.casing_inner_diameter / 1000  # noqa

    def _get_annular_area(self):
        """Площадь межтрубного пространства, м². S = π/4 × (D² - d²)"""
        casing_d = self._get_casing_inner_diameter_m()
        nkt_d = self.nkt_diameter / 1000  # noqa
        return (math.pi / 2) * (casing_d ** 2 - nkt_d ** 2)  # площадь кольца

    def _get_annular_area_for_motor(self, motor_diameter_m):
        """Площадь сечения вокруг ПЭД заданного диаметра, м²"""
        casing_d = self._get_casing_inner_diameter_m()
        return (math.pi / 4) * (casing_d ** 2 - motor_diameter_m ** 2)

    def _get_p_zab(self, target_flow):
        """
        Расчет забойного давления при заданном дебите.
        Args:
            target_flow: целевой дебит, м³/сут
        Returns:
            Забойное давление, атм
        """
        # Если есть все данные для расчета по притоку
        if self.productivity_index and self.reservoir_pressure:
            print('1', self.reservoir_pressure - target_flow / self.productivity_index)
            return self.reservoir_pressure - target_flow / self.productivity_index  # noqa

        # Если есть только пластовое давление
        if self.reservoir_pressure:
            print('2', self.reservoir_pressure * DEFAULT_PRESSURE_FRACTION)
            return self.reservoir_pressure * DEFAULT_PRESSURE_FRACTION  # noqa
        print('3', MIN_BOTTOM_HOLE_PRESSURE)
        # Если нет данных, возвращаем минимум
        return MIN_BOTTOM_HOLE_PRESSURE

    def _get_fluid_velocity_in_nkt(self, target_flow):
        """
            Расчет скорости жидкости в НКТ.
            Args:
                target_flow: дебит жидкости, м³/сут
            Returns:
                Скорость жидкости, м/с
            """
        nkt_area = math.pi * self._get_nkt_inner_diameter() ** 2 / 4
        return target_flow / (SECONDS_IN_DAY * nkt_area)

    @with_defaults
    def _get_dynamic_level(self, target_flow, intake_pressure, **kwargs):
        """
        Расчет динамического уровня жидкости в скважине.
        Динамический уровень - расстояние от устья до уровня жидкости
        в межтрубном пространстве при работе скважины.
        Формула: H_дин = H_спуска - P_заб / (ρ * g)
        где:
            P_заб - забойное давление, МПа
            ρ - плотность жидкости на приеме, кг/м³
            g - ускорение свободного падения, м/с²
        Перевод единиц: 1 МПа = 10⁶ Па
        Args:
            target_flow: целевой дебит, м³/сут
            intake_pressure: давление на приеме насоса, МПа
        Returns:
            float: динамический уровень, м
        """
        props = self.get_fluid_properties_at_intake(target_flow, intake_pressure)
        p_zab_mpa = self._get_p_zab(target_flow)
        p_zab_pa = p_zab_mpa * MPA_TO_PA

        pressure_head = p_zab_pa / (props['density'] * GRAVITY)

        return self.depth - pressure_head  # noqa

    def _get_reynolds_number(self, target_flow):
        """
        Расчет числа Рейнольдса для потока в НКТ.
        Re = v * d / nu
        Args:
            target_flow: дебит жидкости, м³/сут
        Returns:
            float: число Рейнольдса (безразмерное)
        """
        velocity = self._get_fluid_velocity_in_nkt(target_flow)
        diameter = self._get_nkt_inner_diameter()

        return velocity * diameter / WATER_KINEMATIC_VISCOSITY

    @staticmethod
    def _calculate_friction_factor(re):
        """
        Расчет коэффициента гидравлического трения (λ) по числу Рейнольдса.
        Ламинарный режим (Re < 2300): λ = 64/Re
        Турбулентный режим (Re ≥ 2300): λ = 0.3164/Re^0.25 (Блазиус)
        """
        if re <= 0:
            raise ValueError(f"Число Рейнольдса должно быть положительным: {re}")

        if re < 2300:
            return 64 / re

        return 0.3164 / (re ** 0.25)

    def _calculate_friction_loss(self, lambda_coef, velocity, length, gravity=GRAVITY):
        """
        Расчет потерь напора на трение по формуле Дарси-Вейсбаха
        Args:
            lambda_coef: коэффициент гидравлического трения
            velocity: скорость жидкости в НКТ (м/с)
            length: длина участка (глубина спуска насоса), м
            gravity: ускорение свободного падения, м/с²
        Returns:
            Потери напора на трение (м)
        """
        d_inner = self._get_nkt_inner_diameter()

        # h = λ * (L/d) * (v²/2g)
        friction_loss = lambda_coef * (length / d_inner) * (velocity ** 2 / (2 * gravity))

        return friction_loss

    def _get_buffer_head_from_pressure(self, target_flow, intake_pressure):
        """
        Перевод буферного давления из МПа в метры столба жидкости.
        Формула: H_буф = P_буф / (ρ * g)
        где P_буф переводится из МПа в Па (1 МПа = 10⁶ Па)
        Args:
            target_flow: целевой дебит, м³/сут
            intake_pressure: давление на приеме, МПа
        Returns:
            float: буферный напор, м
        """
        props = self.get_fluid_properties_at_intake(target_flow, intake_pressure)
        density = props['density']

        # H = P / (ρ * g) # noqa
        buffer_head = (self.buffer_pressure * MPA_TO_PA) / (density * GRAVITY)  # noqa

        return buffer_head

    def _calculate_gas_lift_effect(self, props):
        """
        Расчет газлифтного эффекта (дополнительного напора за счет газа)
        """
        if props['gas_fraction'] > 0 and self.bubble_point_pressure:
            c_slip = 2e-4 if self.water_cut < 50 else 16e-4
            annular_area = self._get_annular_area()
            phi = props['gas_fraction'] / (1 + c_slip * props['flow_at_intake'] / annular_area)
            p_gas = self.bubble_point_pressure * (1 / (1 - 0.4 * phi) - 1)  # noqa
            h_gas = (p_gas * 1e6) / (props['density'] * GRAVITY)
        else:
            h_gas = 0

        return h_gas

    def get_dynamic_level(self):
        """Публичный метод для получения динамического уровня"""
        return self._get_dynamic_level()

    def get_mixture_density(self, water_cut=None):
        """
        Плотность смеси без учета газа, кг/м2
        Если water_cut не указан, используется значение из модели
        """
        w_cut = water_cut if water_cut is not None else self.water_cut
        oil_fraction = 1 - w_cut / 100
        water_fraction = w_cut / 100
        return self.oil_density * oil_fraction + self.water_density * water_fraction  # noqa

    def get_max_possible_flow(self):
        """Максимально возможный дебит по коэффициенту продуктивности, м3/сут"""
        if self.productivity_index and self.reservoir_pressure:
            p_zab_min = MIN_BOTTOM_HOLE_PRESSURE  # минимальное забойное давление
            return self.productivity_index * (self.reservoir_pressure - p_zab_min)  # noqa
        return None

    def get_recommended_flow(self):
        """
        Рекомендуемый дебит (приоритет у formation_debit если он задан)
        """
        # Если явно задан плановый дебит - используем его
        if self.formation_debit:
            return self.formation_debit

        # Иначе рассчитываем на основе продуктивности
        max_flow = self.get_max_possible_flow()
        if max_flow:
            return max_flow * 0.8

        # Если ничего нет - значение по умолчанию
        return DEFAULT_FLOW

    def get_min_intake_pressure(self):
        """Минимальное давление на приеме насоса, МПа"""
        if self.bubble_point_pressure:
            return 0.75 * self.bubble_point_pressure  # noqa
        return MIN_INTAKE_PRESSURE

    @with_defaults
    def get_fluid_properties_at_intake(self, target_flow, intake_pressure, **kwargs):
        """
        Расчет свойств жидкости на приеме насоса
        Args:
            target_flow: дебит жидкости, м3/сут
            intake_pressure: давление на приеме насоса, МПа
        Returns:
            dict: свойства жидкости на приеме
        """
        # Объемный коэффициент при текущем давлении
        if self.bubble_point_pressure and intake_pressure >= self.bubble_point_pressure:
            b = self.oil_volume_factor  # noqa
            gas_fraction = 0
        elif self.bubble_point_pressure:
            # Формула 8.7 из стандарта
            b = self.water_cut / 100 + (1 - self.water_cut / 100) * (  # noqa
                    1 + (self.oil_volume_factor - 1) * (intake_pressure / self.bubble_point_pressure) ** 0.5  # noqa
            )
            # Объемное газосодержание (формула 8.10)
            gas_fraction = 1 / (
                    (1 + intake_pressure) * b + 1 / (
                    self.gas_factor * (1 - intake_pressure / self.bubble_point_pressure)  # noqa
                )
            )
        else:
            b = 1.0
            gas_fraction = 0

        # Расход на приеме, м³/с
        flow_at_intake = target_flow * b / SECONDS_IN_DAY

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
            'volume_factor': b
        }

    @with_defaults
    def get_pump_depth(self, target_flow=None, intake_pressure=None, **kwargs):
        """
        Возвращает глубину спуска насоса.
        Если пользователь указал - возвращает её.
        Если нет - рассчитывает автоматически.
        """
        # Если пользователь указал глубину - используем её
        if self.pump_depth is not None:
            return self.pump_depth

        # Свойства жидкости на приеме
        props = self.get_fluid_properties_at_intake(target_flow, intake_pressure)
        print('props', props)

        # Динамический уровень
        h_din = self._get_dynamic_level(target_flow, intake_pressure)  # noqa

        # Глубина спуска насоса
        calculated_depth = h_din + (intake_pressure * MPA_TO_PA) / (props['density'] * GRAVITY)

        return calculated_depth

    @with_defaults
    def calculate_required_head(self, target_flow, intake_pressure=None, **kwargs):
        """
        Расчет потребного напора насоса для заданного дебита
        Args:
            target_flow: Планируемый дебит, м³/сут
            intake_pressure: Давление на приеме
        Returns:
            float: Потребный напор насоса, м
        """
        # Свойства жидкости на приеме
        props = self.get_fluid_properties_at_intake(target_flow, intake_pressure)

        # Глубина спуска насоса
        l_pump = self.get_pump_depth(target_flow, intake_pressure)

        # Скорость жидкости в НКТ
        velocity = self._get_fluid_velocity_in_nkt(target_flow)

        # Число Рейнольдса
        re = self._get_reynolds_number(target_flow)

        # Определяем коэффициент гидравлического трения (λ) в зависимости от режима течения
        lambda_coef = self._calculate_friction_factor(re)

        # Рассчитываем потери напора на трение в НКТ по формуле Дарси-Вейсбаха
        h_tr = self._calculate_friction_loss(
            lambda_coef=lambda_coef,
            velocity=velocity,
            length=l_pump
        )

        # Буферное давление в метрах
        h_buf = self._get_buffer_head_from_pressure(target_flow, intake_pressure)

        # Газлифтный эффект
        h_gas = self._calculate_gas_lift_effect(props)

        # ИТОГО: потребный напор
        required_head = l_pump + h_buf + h_tr - h_gas

        return required_head

    def get_static_level(self):
        """
        Расчет статического уровня жидкости в скважине
        """
        # Пластовое давление в Паскалях
        p_res_pa = self.reservoir_pressure * 1e6

        # Буферное давление в Паскалях
        p_buf_pa = self.buffer_pressure * 1e6

        # Плотность смеси
        density = self.get_mixture_density()

        g = 9.81

        # Высота столба жидкости от забоя до уровня
        liquid_column = (p_res_pa - p_buf_pa) / (density * g)

        # Статический уровень = глубина скважины - высота столба
        static_level = self.depth - liquid_column

        return static_level

    def get_dynamic_level_from_telemetry(self, intake_pressure_mpa=None):
        """
        Расчет динамического уровня по давлению на приеме из телеметрии

        Args:
            intake_pressure_mpa: давление на приеме, МПа (если None - берет из последней телеметрии)
        """
        # Если давление не передано, берем из последней телеметрии
        if intake_pressure_mpa is None:
            last_telemetry = self.telemetry.order_by('-timestamp').first()
            if last_telemetry and last_telemetry.intake_pressure:
                intake_pressure_mpa = last_telemetry.intake_pressure / 9.87  # атм → МПа
                print('Давление на приеме из телеметрии', intake_pressure_mpa)
            else:
                return None

        # Глубина спуска насоса
        pump_depth = self.get_pump_depth()

        # Плотность жидкости на приеме (с учетом газа)
        props = self.get_fluid_properties_at_intake()
        density = props['density']  # кг/м³

        # Перевод давления из МПа в Па
        pressure_pa = intake_pressure_mpa * 1e6

        # Высота столба жидкости над насосом
        liquid_column = pressure_pa / (density * 9.81)
        print('Плотность жидкости на приеме (с учетом газа)', density)
        print('Высота столба жидкости над насосом', liquid_column)
        print('Глубина спуска насоса', pump_depth)
        # Динамический уровень
        dynamic_level = pump_depth - liquid_column

        return dynamic_level

    @with_defaults
    def get_full_engineering_report(self, target_flow=None, intake_pressure=None, **kwargs):
        """
        Полный инженерный отчет по скважине

        Args:
            target_flow: Целевой дебит (если None - берется рекомендованный)
            intake_pressure: Давление на приеме (если None - берется минимальное)

        Returns:
            dict: Все расчетные параметры для отображения инженеру
        """
        # Получаем свойства на приеме
        props = self.get_fluid_properties_at_intake(target_flow, intake_pressure)

        # Собираем полный отчет
        report = {
            'input_data': self._get_input_parameters(),                                     # 📋 Исходные данные
            'reservoir': self._get_reservoir_parameters(target_flow, intake_pressure),      # ⛽ Параметры пласта
            'fluid': self._get_fluid_properties(),                                          # 💧 Свойства жидкости
            'intake': self._get_intake_parameters(props, intake_pressure),
            'hydraulics': self._get_hydraulics_parameters(target_flow, props),
            'head_components': self._get_head_components(target_flow, intake_pressure, props),
            'recommendations': self._get_recommendations(props),
            'metadata': {
                'report_generated': datetime.now().isoformat(),
                'target_flow_used': target_flow,
                'intake_pressure_used': intake_pressure,
                'calculation_method': 'СТО ТН 229-2017 / ТУ 3631-015-87867182-2009'
            }
        }

        return report

    def _get_input_parameters(self):
        """
        Исходные данные скважины (что хранится в БД)
        """
        return {
            # Основная информация
            'name': self.name,
            'external_id': self.external_id,
            'is_active': self.is_active,

            # Геология
            'depth': self.depth,
            'reservoir_pressure': self.reservoir_pressure,
            'productivity_index': self.productivity_index,
            'casing_diameter': self.casing_inner_diameter,

            # Свойства жидкости
            'oil_density': self.oil_density,
            'water_density': self.water_density,
            'gas_factor': self.gas_factor,
            'water_cut': self.water_cut,
            'bubble_point_pressure': self.bubble_point_pressure,
            'oil_volume_factor': self.oil_volume_factor,

            # Конструкция
            'nkt_diameter': self.nkt_diameter,
            'nkt_wall_thickness': self.nkt_wall_thickness,
            'buffer_pressure': self.buffer_pressure,

            # Эксплуатация
            'formation_debit': self.formation_debit,
            'pump_depth_input': self.pump_depth,

            # Системные
            'created_at': self.created_at.isoformat() if self.created_at else None,  # noqa
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,  # noqa
        }

    def _get_reservoir_parameters(self, target_flow, intake_pressure):
        """
        Расчет параметров пласта при заданном дебите
        с учетом свойств жидкости на приеме
        Args:
            target_flow: Целевой дебит (м³/сут)
            props: Словарь со свойствами на приеме (из get_fluid_properties_at_intake)
        """
        # Забойное давление по формуле притока
        p_zab = self._get_p_zab(target_flow)
        depression = self.reservoir_pressure - p_zab if self.reservoir_pressure else 0  # noqa

        # Динамический уровень
        h_din = self._get_dynamic_level(target_flow, intake_pressure)

        # Максимальный дебит
        max_flow = self.get_max_possible_flow()

        return {
            'reservoir_pressure': round(self.reservoir_pressure, 2) if self.reservoir_pressure else None,  # noqa
            'productivity_index': round(self.productivity_index, 2) if self.productivity_index else None,  # noqa
            'target_flow': round(target_flow, 1),
            'bottom_hole_pressure': round(p_zab, 2),
            'depression': round(depression, 2),
            'dynamic_level': round(h_din, 1),
            'max_possible_flow': round(max_flow, 1) if max_flow else None,
            'flow_percent_of_max': round((target_flow / max_flow * 100), 1) if max_flow else None,
        }

    def _get_fluid_properties(self):
        """
        Базовые свойства пластовой жидкости (без учета давления)
        """
        # Плотность смеси без газа
        rho_mix_no_gas = self.get_mixture_density()

        return {
            'oil_density': round(self.oil_density, 1),  # noqa
            'water_density': round(self.water_density, 1),  # noqa
            'gas_factor': round(self.gas_factor, 1),  # noqa
            'water_cut': round(self.water_cut, 1),  # noqa
            'bubble_point_pressure': round(self.bubble_point_pressure, 2) if self.bubble_point_pressure else None,  # noqa
            'oil_volume_factor': round(self.oil_volume_factor, 3),  # noqa
            'mixture_density_no_gas': round(rho_mix_no_gas, 1),
            'is_gas_present': self.bubble_point_pressure is not None,
        }

    def _get_intake_parameters(self, props, intake_pressure):
        """
        Параметры на приеме насоса (с учетом газа)
        """
        print(f"🔥 _get_intake_parameters: intake_pressure={intake_pressure}")
        print(f"🔥 props keys: {props.keys() if props else None}")
        # Минимально допустимое давление
        min_pressure = self.get_min_intake_pressure()

        # ЗАЩИТА ОТ None
        if intake_pressure is None or min_pressure is None:
            pressure_margin = None
        else:
            pressure_margin = intake_pressure - min_pressure

        # Проверка необходимости газосепаратора
        need_separator = props['gas_fraction'] > 0.25 if props['gas_fraction'] is not None else False
        gas_status = "⚠️ Требуется газосепаратор!" if need_separator else "✓ Норма"
        gas_color = "danger" if need_separator else "success"

        return {
            'intake_pressure': round(intake_pressure, 2) if intake_pressure is not None else None,
            'min_intake_pressure': round(min_pressure, 2) if min_pressure is not None else None,
            'pressure_margin': round(pressure_margin, 2) if pressure_margin is not None else None,
            'pressure_status': "выше мин." if pressure_margin and pressure_margin > 0 else "НИЖЕ МИН.!",
            'pressure_color': "success" if pressure_margin and pressure_margin > 1 else
            "warning" if pressure_margin and pressure_margin > 0 else "danger",

            'gas_fraction': round(props['gas_fraction'] * 100, 1) if props['gas_fraction'] is not None else None,
            'gas_fraction_limit': 25.0,
            'gas_status': gas_status,
            'gas_color': gas_color,
            'need_separator': need_separator,

            'density': round(props['density'], 1) if props['density'] is not None else None,
            'density_no_gas': round(self.get_mixture_density(), 1),
            'density_diff': round(props['density'] - self.get_mixture_density(), 1)
            if props['density'] is not None else None,

            'volume_factor': round(props['volume_factor'], 3) if props['volume_factor'] is not None else None,
            'flow_at_intake_m3s': round(props['flow_at_intake'], 6) if props['flow_at_intake'] is not None else None,
            'flow_at_intake_m3day': round(props['flow_at_intake'] * 86400, 1) if props[
                                                                                     'flow_at_intake'] is not None else None,
        }

    def _get_hydraulics_parameters(self, target_flow, props):
        """
        Гидравлические параметры потока в НКТ
        """

        # Геометрия
        nkt_area = math.pi * self._get_nkt_inner_diameter() ** 2 / 4  # площадь в м²

        # СКОРОСТЬ: target_flow в м³/сут, переводим в м³/с
        velocity = self._get_fluid_velocity_in_nkt(target_flow)  # м/с

        # Число Рейнольдса (ν = 1e-6 м²/с для воды)
        re = self._get_reynolds_number(target_flow)

        # Режим течения и коэффициент трения
        if re < 2300:
            lambda_coef = self._calculate_friction_factor(re)
            flow_regime = "ламинарный"
        else:
            lambda_coef = self._calculate_friction_factor(re)
            flow_regime = "турбулентный"

        # Потери на трение на 1000 м (удельные)
        h_tr_per_1000 = lambda_coef * (1000 / self._get_nkt_inner_diameter()) * (velocity ** 2 / (2 * GRAVITY))

        return {
            'nkt_inner_diameter_mm': round(self._get_nkt_inner_diameter() * 1000, 1),
            'nkt_area_cm2': round(nkt_area * 10000, 2),
            'velocity': velocity,
            'reynolds': round(re, 0),
            'flow_regime': flow_regime,
            'lambda_coef': lambda_coef,
            'friction_loss_per_1000m': round(h_tr_per_1000, 2),
            'friction_formula': "Блазиуса" if re >= 2300 else "Стокса",
        }

    def _get_head_components(self, target_flow, intake_pressure, props):
        """
        Все составляющие потребного напора насоса
        """

        # Забойное давление
        p_zab = self._get_p_zab(target_flow)

        # Давление на приеме (минимальное)
        p_intake = self.get_min_intake_pressure()

        # Динамический уровень
        h_din = self._get_dynamic_level(target_flow, intake_pressure)

        # Глубина спуска насоса
        l_pump = h_din + (p_intake * 1e6) / (props['density'] * GRAVITY)

        # Потери на трение
        velocity = self._get_fluid_velocity_in_nkt(target_flow)
        re = self._get_reynolds_number(target_flow)

        lambda_coef = self._calculate_friction_factor(re)

        h_tr = self._calculate_friction_loss(
            lambda_coef=lambda_coef,
            velocity=velocity,
            length=l_pump
        )

        # Буферное давление в метрах
        h_buf = self._get_buffer_head_from_pressure(target_flow, intake_pressure)

        # Газлифтный эффект
        h_gas = self._calculate_gas_lift_effect(props)

        # Итоговый напор
        total_head = self.calculate_required_head(target_flow, intake_pressure)

        return {
            'components': {
                'pump_depth': {
                    'value': round(l_pump, 1),
                    'description': 'Глубина спуска насоса',
                    'formula': 'H_дин + P_пр/ρg'
                },
                'buffer_head': {
                    'value': round(h_buf, 1),
                    'description': 'Буферное давление',
                    'formula': 'P_буф/ρg'
                },
                'friction_head': {
                    'value': round(h_tr, 1),
                    'description': 'Потери на трение',
                    'formula': 'λ·L/d·v²/2g'
                },
                'gas_lift_head': {
                    'value': round(h_gas, 1),
                    'description': 'Газлифтный эффект (вычитается)',
                    'formula': 'P_газ/ρg'
                }
            },
            'total_head': total_head,
            'total_head_formula': 'L + h_буф + h_тр - h_газ',
            'dynamic_level': round(h_din, 1),
            'intake_pressure_used': round(p_intake, 2),
        }

    def _get_recommendations(self, props):
        """
        Рекомендации по эксплуатации на основе расчетов
        """
        recommendations = []

        # 1. Проверка газосодержания
        if props['gas_fraction'] > 0.25:
            recommendations.append({
                'type': 'warning',
                'parameter': 'Газ',
                'message': f'Газосодержание {props["gas_fraction"] * 100:.1f}% превышает допустимые 25%',
                'action': 'Рекомендуется установка газосепаратора',
                'icon': 'gas-pump'
            })
        elif props['gas_fraction'] > 0.15:
            recommendations.append({
                'type': 'info',
                'parameter': 'Газ',
                'message': f'Газосодержание {props["gas_fraction"] * 100:.1f}% (в пределах нормы)',
                'action': 'Газосепаратор не требуется, но рекомендуется контроль',
                'icon': 'chart-line'
            })
        else:
            recommendations.append({
                'type': 'success',
                'parameter': 'Газ',
                'message': f'Газосодержание {props["gas_fraction"] * 100:.1f}% (в пределах нормы)',
                'action': 'Газосепаратор не требуется',
                'icon': 'check-circle'
            })

        # 2. Рекомендации по НКТ (скорость потока)
        nkt_area = math.pi * self._get_nkt_inner_diameter() ** 2 / 4
        # Для скорости используем target_flow, но у нас его нет в этом методе
        # Добавим заглушку, в финальной версии нужно передавать target_flow

        # 3. Рекомендации по динамическому уровню
        # Будет добавлено позже с полными данными

        # 4. Рекомендации по типоразмеру насоса
        # Будет добавлено после подбора

        return recommendations


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

    def calculate_at_point(self, q_value):
        """
        Calculate pump parameters at given flow rate.
        """
        # Добавьте проверки перед интерполяцией
        if not self.q_values or not self.h_values:
            return {
                'q': q_value,
                'h': 0,
                'n': 0,
                'kpd': 0,
                'is_in_working_range': False,
                'is_optimal': False
            }

        # Проверка, что q_value в пределах массива
        if q_value <= self.q_values[0]:
            h = self.h_values[0]
            n = self.n_values[0] if self.n_values else 0
            kpd = self.kpd_values[0] if self.kpd_values else 0
        elif q_value >= self.q_values[-1]:
            h = self.h_values[-1]
            n = self.n_values[-1] if self.n_values else 0
            kpd = self.kpd_values[-1] if self.kpd_values else 0
        else:
            # Интерполяция
            h = self._interpolate(self.q_values, self.h_values, q_value)
            n = self._interpolate(self.q_values, self.n_values, q_value) if self.n_values else 0
            kpd = self._interpolate(self.q_values, self.kpd_values, q_value) if self.kpd_values else 0

        is_optimal = False
        if self.optimal_flow_range and len(self.optimal_flow_range) == 2:
            is_optimal = self.optimal_flow_range[0] <= q_value <= self.optimal_flow_range[1]

        return {
            'q': q_value,
            'h': h,
            'n': n,
            'kpd': kpd,
            'is_in_working_range': self.left_range <= q_value <= self.right_range,
            'is_optimal': is_optimal,
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
    interturn_test_voltage = models.FloatField(
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
            models.Index(fields=['-timestamp']),
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
