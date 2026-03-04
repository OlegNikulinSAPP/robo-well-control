from datetime import timezone, timedelta
from django.utils import timezone
from core.models import Alert, TelemetryData, Well


class AlertService:
    """Сервис для проверки пороговых значений."""

    THRESHOLDS = {
        'pressure': {'warning': 30, 'critical': 120},
        'temperature': {'warning': 60, 'critical': 95},
        'vibration': {'warning': 0.5, 'critical': 7.1},
        'current_unbalance': {'warning': 5, 'critical': 20},
    }

    @classmethod
    def check_telemetry(cls, telemetry):
        """Проверка одной записи телеметрии."""
        alerts = []

        # Проверка давления
        if telemetry.intake_pressure:
            alerts.extend(cls._check_value(
                telemetry, 'pressure', telemetry.intake_pressure,
                "Давление на приеме"
            ))

        # Проверка температуры
        if telemetry.intake_temperature:
            alerts.extend(cls._check_value(
                telemetry, 'temperature', telemetry.intake_temperature,
                "Температура на приеме"
            ))

        # Проверка вибрации
        if telemetry.vibration_x:
            alerts.extend(cls._check_value(
                telemetry, 'vibration', telemetry.vibration_x,
                "Вибрация по оси X"
            ))
        if telemetry.vibration_y:
            alerts.extend(cls._check_value(
                telemetry, 'vibration', telemetry.vibration_y,
                "Вибрация по оси Y"
            ))

        # Проверка дисбаланса токов
        unbalance = telemetry.current_unbalance()
        if unbalance:
            alerts.extend(cls._check_value(
                telemetry, 'current_unbalance', unbalance,
                "Дисбаланс токов"
            ))

        return alerts

    @classmethod
    def _check_value(cls, telemetry, param_type, value, param_name):
        """Проверка одного параметра."""
        alerts = []
        thresholds = cls.THRESHOLDS.get(param_type, {})

        print(
            f"Checking {param_type}: value={value}, warning={thresholds.get('warning')}, critical={thresholds.get('critical')}")

        if not thresholds:
            return alerts

        if value >= thresholds.get('critical', float('inf')):
            severity = 'critical'
            message = f"{param_name}: {value:.1f} (критично! порог {thresholds['critical']})"
        elif value >= thresholds.get('warning', float('inf')):
            severity = 'warning'
            message = f"{param_name}: {value:.1f} (превышение порога {thresholds['warning']})"
        else:
            return alerts

        # Проверяем, не было ли уже такого уведомления за последний час
        recent = Alert.objects.filter(
            well=telemetry.well,
            alert_type=param_type,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()

        if not recent:
            alert = Alert.objects.create(
                well=telemetry.well,
                alert_type=param_type,
                severity=severity,
                message=message,
                value=value,
                threshold=thresholds.get('warning' if severity == 'warning' else 'critical')
            )
            alerts.append(alert)

        return alerts

    @classmethod
    def check_latest_for_well(cls, well):
        """Проверка последних данных для скважины."""
        latest = well.telemetry.first()
        if latest:
            return cls.check_telemetry(latest)
        return []

    @classmethod
    def check_all_wells(cls):
        """Проверка всех скважин."""
        alerts = []
        for well in Well.objects.all():
            alerts.extend(cls.check_latest_for_well(well))
        return alerts