from django.contrib import admin
from .models import Well, ElectricMotor, PumpCharacteristic, TelemetryData, Alert, CommandLog


class TelemetryInline(admin.TabularInline):
    model = TelemetryData
    extra = 0
    fields = ('timestamp', 'intake_pressure', 'intake_temperature', 'current_phase_a')
    readonly_fields = ('timestamp',)
    max_num = 10


@admin.register(Well)
class WellAdmin(admin.ModelAdmin):
    """Админка для модели Well"""

    list_display = (
        'name', 'depth', 'reservoir_pressure', 'productivity_index',
        'formation_debit', 'water_cut', 'is_active', 'created_at'
    )

    list_filter = ('is_active', 'water_cut', 'created_at')
    search_fields = ('name', 'external_id')
    ordering = ('-created_at',)

    inlines = [TelemetryInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'external_id', 'is_active')
        }),
        ('Геологические параметры', {
            'fields': ('depth', 'reservoir_pressure', 'productivity_index')
        }),
        ('Параметры жидкости', {
            'fields': ('oil_density', 'water_density', 'gas_factor', 'water_cut',
                       'bubble_point_pressure', 'oil_volume_factor')
        }),
        ('Конструкция скважины', {
            'fields': ('casing_inner_diameter', 'nkt_diameter', 'nkt_wall_thickness',
                       'buffer_pressure', 'formation_debit', 'pump_depth')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    # Действия в админке
    actions = ['make_active', 'make_inactive']

    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    make_active.short_description = "Активировать выбранные скважины"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    make_inactive.short_description = "Деактивировать выбранные скважины"

    # Кастомное отображение для обводненности
    def water_cut_display(self, obj):
        return f"{obj.water_cut}%"

    water_cut_display.short_description = "Обводненность"
    water_cut_display.admin_order_field = 'water_cut'


@admin.register(ElectricMotor)
class ElectricMotorAdmin(admin.ModelAdmin):
    list_display = ('model', 'manufacturer', 'nominal_power', 'nominal_voltage', 'efficiency', 'is_active')
    list_filter = ('manufacturer', 'is_active')
    search_fields = ('model', 'motor_id', 'manufacturer')
    list_per_page = 20


@admin.register(PumpCharacteristic)
class PumpCharacteristicAdmin(admin.ModelAdmin):
    list_display = ('harka_stupen', 'cod', 'zavod', 'nominal_range', 'max_efficiency', 'stages_count', 'is_active')
    list_filter = ('zavod', 'material_stupen', 'is_active')
    search_fields = ('harka_stupen', 'cod')
    list_per_page = 20


@admin.register(TelemetryData)
class TelemetryDataAdmin(admin.ModelAdmin):
    list_display = ('well', 'timestamp', 'intake_pressure', 'intake_temperature')
    list_filter = ('well', 'timestamp')
    ordering = ('-timestamp',)
    list_per_page = 50


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('well', 'alert_type', 'severity', 'message', 'is_read', 'created_at')
    list_filter = ('well', 'severity', 'alert_type', 'is_read')
    ordering = ('-created_at',)
    list_per_page = 50


@admin.register(CommandLog)
class CommandLogAdmin(admin.ModelAdmin):
    list_display = ('well', 'command_type', 'status', 'created_at')
    list_filter = ('well', 'command_type', 'status')
    ordering = ('-created_at',)
    list_per_page = 50
