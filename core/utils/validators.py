import re
from django.core.exceptions import ValidationError

def validate_frequency(value):
    """Проверка допустимого диапазона частоты."""
    if not 30 <= value <= 60:
        raise ValidationError(f"Частота {value} Гц вне допустимого диапазона (30-60 Гц)")
    return value

def validate_current(value):
    """Проверка допустимого тока."""
    if value <= 0:
        raise ValidationError(f"Ток {value} А должен быть положительным")
    if value > 200:
        raise ValidationError(f"Ток {value} А превышает максимальный (200 А)")
    return value

def validate_well_id(well_id):
    """Проверка формата ID скважины."""
    if not re.match(r'^[A-Za-z0-9_-]+$', str(well_id)):
        raise ValidationError(f"Неверный формат ID скважины: {well_id}")
    return well_id

def validate_command_type(command_type):
    """Проверка типа команды."""
    valid_types = ['frequency_adjust', 'start', 'stop', 'emergency_stop']
    if command_type not in valid_types:
        raise ValidationError(f"Неизвестный тип команды: {command_type}")
    return command_type