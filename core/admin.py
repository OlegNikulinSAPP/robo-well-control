from django.contrib import admin
from .models import Well, ElectricMotor, PumpCharacteristic


@admin.register(Well)
class WellAdmin(admin.ModelAdmin):
    @admin.display(description='Номер скважины', ordering='name')
    def name_column(self, obj):
        return obj.name

    @admin.display(description='Глубина скважины, м', ordering='depth')
    def depth_column(self, obj):
        return obj.depth

    @admin.display(description='Диаметр колонны, мм', ordering='diameter')
    def diameter_column(self, obj):
        return obj.diameter

    @admin.display(description='Глубина спуска насоса, м', ordering='pump_depth')
    def pump_depth_column(self, obj):
        return obj.pump_depth

    @admin.display(description='Статический уровень, м', ordering='static_level')
    def static_level_column(self, obj):
        return obj.static_level


    @admin.display(description='Дебит скважины, м³/сутки', ordering='formation_debit')
    def formation_debit_column(self, obj):
        return obj.formation_debit

    @admin.display(description='Дата создания', ordering='created_at')
    def created_at_column(self, obj):
        return obj.created_at

    @admin.display(description='Дата обновления', ordering='updated_at')
    def updated_at_column(self, obj):
        return obj.updated_at

    list_display = (
        'name_column',
        'depth_column',
        'diameter_column',
        'pump_depth_column',
        'dynamic_level_column',
        'formation_debit_column',
        'created_at_column',
        'updated_at_column'
    )

    list_filter = ('created_at',)
    search_fields = ('name',)
    ordering = ('name',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'depth', 'diameter'),
            'description': 'Геологические и конструктивные параметры скважины'
        }),
        ('Эксплуатационные параметры', {
            'fields': ('pump_depth', 'dynamic_level', 'static_level', 'formation_debit'),
            'description': 'Параметры работы и продуктивности скважины'
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'description': 'Системная информация',
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20


@admin.register(ElectricMotor)
class ElectricMotorAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для электродвигателей.
    """
    list_display = (
        'motor_type',
        'manufacturer',
        'nominal_power',
        'nominal_voltage',
        'nominal_current',
        'is_active'
    )

    list_filter = (
        'manufacturer',
        'insulation_class',
        'is_active'
    )

    search_fields = (
        'motor_type',
        'manufacturer'
    )

    fieldsets = (
        ('Основные параметры', {
            'fields': (
                'motor_type',
                'manufacturer',
                'nominal_power',
                'nominal_voltage',
                'nominal_current'
            )
        }),
        ('Электрические характеристики', {
            'fields': (
                'efficiency',
                'power_factor',
                'nominal_slip',
                'insulation_resistance'
            )
        }),
        ('Механические характеристики', {
            'fields': (
                'min_well_diameter',
                'coolant_velocity',
                'shaft_torque'
            )
        }),
        ('Конструктивные параметры', {
            'fields': (
                'insulation_class',
                'protection_class',
                'weight',
                'dimensions',
                'sections_count'
            )
        }),
        ('Системные', {
            'fields': (
                'is_active',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    class Meta:
        verbose_name = 'Электродвигатель'
        verbose_name_plural = 'Электродвигатели'


@admin.register(PumpCharacteristic)
class PumpCharacteristicAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для характеристик насосов ЭЦН.
    """
    list_display = (
        'harka_stupen',
        'cod',
        'zavod',
        'nominal_range',
        'nominal_head',
        'max_efficiency',  # Добавили
        'max_efficiency_flow',  # Добавили
        'stages_count',
        'is_active'
    )

    list_filter = (
        'zavod',
        'material_stupen',
        'is_active'
    )

    search_fields = (
        'harka_stupen',
        'cod',
        'zavod'
    )

    fieldsets = (
        ('Идентификация', {
            'fields': (
                'cod',
                'harka_stupen',
                'zavod',
                'material_stupen',
                'source_file'
            )
        }),
        ('Рабочие диапазоны', {
            'fields': (
                'left_range',
                'nominal_range',
                'right_range',
                'min_kpd_rosneft'
            )
        }),
        ('Технические характеристики', {
            'fields': (
                'nominal_head',
                'stages_count',
                'housing_diameter',
                'flow_part_material',
                'max_efficiency',  # Добавили
                'max_efficiency_flow'  # Добавили
            )
        }),
        ('Характеристики (JSON)', {
            'fields': (
                'q_values',
                'h_values',
                'n_values',
                'kpd_values'
            ),
            'description': 'Данные для построения характеристик'
        }),
        ('Оптимальные параметры', {  # Новая секция
            'fields': (
                'optimal_flow_range',
            ),
            'description': 'Автоматически рассчитанные оптимальные параметры'
        }),
        ('Системные', {
            'fields': (
                'is_active',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'optimal_flow_range'
    )

    list_per_page = 20

    # Показываем предпросмотр характеристик
    def view_characteristics(self, obj):
        return f"Q: {len(obj.q_values)} точек, H: {len(obj.h_values)} точек"

    view_characteristics.short_description = 'Точек характеристик'

    class Meta:
        verbose_name = 'Насос ЭЦН'
        verbose_name_plural = 'Насосы ЭЦН'
