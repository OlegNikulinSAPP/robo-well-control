from django.contrib import admin
from .models import Well, ElectricMotor, PumpCharacteristic, TelemetryData, Alert, CommandLog


@admin.register(Well)
class WellAdmin(admin.ModelAdmin):
    """Admin interface for Well model."""

    list_display = (
        'name', 'depth', 'formation_debit', 'water_cut',
        'gas_factor', 'productivity_index', 'is_active'
    )

    list_filter = ('is_active', 'water_cut')
    search_fields = ('name', 'external_id')
    ordering = ('name',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'external_id', 'is_active')
        }),
        ('Геологические параметры', {
            'fields': ('depth', 'reservoir_pressure', 'productivity_index',
                      'casing_inner_diameter')
        }),
        ('Параметры жидкости', {
            'fields': ('oil_density', 'water_density', 'gas_factor', 'water_cut',
                      'bubble_point_pressure', 'oil_volume_factor')
        }),
        ('Конструкция скважины', {
            'fields': ('nkt_diameter', 'nkt_wall_thickness', 'buffer_pressure')
        }),
        ('Эксплуатационные параметры', {
            'fields': ('formation_debit', 'pump_depth')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20


@admin.register(ElectricMotor)
class ElectricMotorAdmin(admin.ModelAdmin):
    """Admin interface for ElectricMotor model."""

    list_display = (
        'model', 'manufacturer', 'nominal_power',
        'nominal_voltage', 'efficiency', 'is_active'
    )

    list_filter = ('manufacturer', 'is_active')
    search_fields = ('model', 'motor_id', 'manufacturer')

    fieldsets = (
        ('Identification', {
            'fields': ('motor_id', 'model', 'manufacturer')
        }),
        ('Nominal Parameters', {
            'fields': ('nominal_power', 'nominal_voltage', 'nominal_current')
        }),
        ('Mechanical', {
            'fields': ('rotation_speed', 'torque', 'shaft_torque', 'vibration_level')
        }),
        ('Electrical', {
            'fields': ('efficiency', 'power_factor', 'slip')
        }),
        ('Insulation', {
            'fields': ('insulation_resistance', 'insulation_test_voltage')
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20


@admin.register(PumpCharacteristic)
class PumpCharacteristicAdmin(admin.ModelAdmin):
    """Admin interface for PumpCharacteristic model."""

    list_display = (
        'harka_stupen', 'cod', 'zavod', 'nominal_range',
        'max_efficiency', 'stages_count', 'is_active'
    )

    list_filter = ('zavod', 'material_stupen', 'is_active')
    search_fields = ('harka_stupen', 'cod')

    fieldsets = (
        ('Identification', {
            'fields': ('cod', 'harka_stupen', 'zavod', 'material_stupen', 'source_file')
        }),
        ('Operating Ranges', {
            'fields': ('left_range', 'nominal_range', 'right_range', 'min_kpd_rosneft')
        }),
        ('Technical Parameters', {
            'fields': ('nominal_head', 'stages_count', 'housing_diameter', 'flow_part_material')
        }),
        ('Efficiency', {
            'fields': ('max_efficiency', 'max_efficiency_flow', 'optimal_flow_range')
        }),
        ('Motor', {
            'fields': ('recommended_motor',)
        }),
        ('System', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ('created_at', 'updated_at', 'optimal_flow_range')
    list_per_page = 20


@admin.register(TelemetryData)
class TelemetryDataAdmin(admin.ModelAdmin):
    """Admin interface for TelemetryData model."""

    list_display = ('well', 'timestamp', 'intake_pressure', 'intake_temperature')
    list_filter = ('well', 'timestamp')
    ordering = ('-timestamp',)
    list_per_page = 50


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin interface for Alert model."""

    list_display = ('well', 'alert_type', 'severity', 'message', 'is_read', 'created_at')
    list_filter = ('well', 'severity', 'alert_type', 'is_read')
    ordering = ('-created_at',)
    list_per_page = 50


@admin.register(CommandLog)
class CommandLogAdmin(admin.ModelAdmin):
    """Admin interface for CommandLog model."""

    list_display = ('well', 'command_type', 'status', 'created_at')
    list_filter = ('well', 'command_type', 'status')
    ordering = ('-created_at',)
    list_per_page = 50
