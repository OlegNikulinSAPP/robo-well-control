import os
import django
import random

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Well
from django.core.validators import MinValueValidator, MaxValueValidator


def create_test_wells():
    """Создание тестовых скважин для проверки подбора оборудования"""

    wells_data = [
        {
            'name': 'Скважина №1 (девон)',
            'external_id': 'WELL-001',
            'depth': 2500.0,
            'reservoir_pressure': 17.0,
            'productivity_index': 40.0,
            'casing_inner_diameter': 130.0,
            'oil_density': 810.0,
            'water_density': 1170.0,
            'gas_factor': 60.0,
            'water_cut': 45.0,
            'bubble_point_pressure': 9.0,
            'oil_volume_factor': 1.25,
            'nkt_diameter': 73.0,
            'nkt_wall_thickness': 5.5,
            'buffer_pressure': 1.2,
            'formation_debit': 200.0,
            'pump_depth': None,  # будет рассчитано автоматически
            'is_active': True
        },
        {
            'name': 'Скважина №2 (карбон)',
            'external_id': 'WELL-002',
            'depth': 1200.0,
            'reservoir_pressure': 11.0,
            'productivity_index': 15.0,
            'casing_inner_diameter': 130.0,
            'oil_density': 870.0,
            'water_density': 1160.0,
            'gas_factor': 20.0,
            'water_cut': 70.0,
            'bubble_point_pressure': 4.0,
            'oil_volume_factor': 1.1,
            'nkt_diameter': 73.0,
            'nkt_wall_thickness': 5.5,
            'buffer_pressure': 1.0,
            'formation_debit': 80.0,
            'pump_depth': None,
            'is_active': True
        },
        {
            'name': 'Скважина №3 (девон, высокодебитная)',
            'external_id': 'WELL-003',
            'depth': 2600.0,
            'reservoir_pressure': 18.0,
            'productivity_index': 80.0,
            'casing_inner_diameter': 146.0,
            'oil_density': 800.0,
            'water_density': 1180.0,
            'gas_factor': 70.0,
            'water_cut': 30.0,
            'bubble_point_pressure': 10.0,
            'oil_volume_factor': 1.3,
            'nkt_diameter': 89.0,
            'nkt_wall_thickness': 6.5,
            'buffer_pressure': 1.5,
            'formation_debit': 350.0,
            'pump_depth': None,
            'is_active': True
        },
        {
            'name': 'Скважина №4 (карбон, низкодебитная)',
            'external_id': 'WELL-004',
            'depth': 1000.0,
            'reservoir_pressure': 9.0,
            'productivity_index': 5.0,
            'casing_inner_diameter': 130.0,
            'oil_density': 880.0,
            'water_density': 1150.0,
            'gas_factor': 10.0,
            'water_cut': 85.0,
            'bubble_point_pressure': 3.0,
            'oil_volume_factor': 1.05,
            'nkt_diameter': 60.0,
            'nkt_wall_thickness': 5.0,
            'buffer_pressure': 0.8,
            'formation_debit': 40.0,
            'pump_depth': None,
            'is_active': True
        },
        {
            'name': 'Скважина №5 (девон, газовый фактор высокий)',
            'external_id': 'WELL-005',
            'depth': 2400.0,
            'reservoir_pressure': 16.0,
            'productivity_index': 35.0,
            'casing_inner_diameter': 130.0,
            'oil_density': 805.0,
            'water_density': 1170.0,
            'gas_factor': 90.0,
            'water_cut': 20.0,
            'bubble_point_pressure': 12.0,
            'oil_volume_factor': 1.35,
            'nkt_diameter': 73.0,
            'nkt_wall_thickness': 5.5,
            'buffer_pressure': 1.3,
            'formation_debit': 250.0,
            'pump_depth': None,
            'is_active': True
        },
        {
            'name': 'Скважина №6 (карбон, обводненная)',
            'external_id': 'WELL-006',
            'depth': 1100.0,
            'reservoir_pressure': 10.0,
            'productivity_index': 12.0,
            'casing_inner_diameter': 130.0,
            'oil_density': 865.0,
            'water_density': 1165.0,
            'gas_factor': 15.0,
            'water_cut': 95.0,
            'bubble_point_pressure': 3.5,
            'oil_volume_factor': 1.08,
            'nkt_diameter': 73.0,
            'nkt_wall_thickness': 5.5,
            'buffer_pressure': 0.9,
            'formation_debit': 60.0,
            'pump_depth': None,
            'is_active': True
        },
        {
            'name': 'Скважина №7 (неактивная)',
            'external_id': 'WELL-007',
            'depth': 1800.0,
            'reservoir_pressure': 14.0,
            'productivity_index': 25.0,
            'casing_inner_diameter': 130.0,
            'oil_density': 830.0,
            'water_density': 1170.0,
            'gas_factor': 45.0,
            'water_cut': 50.0,
            'bubble_point_pressure': 7.0,
            'oil_volume_factor': 1.2,
            'nkt_diameter': 73.0,
            'nkt_wall_thickness': 5.5,
            'buffer_pressure': 1.1,
            'formation_debit': 150.0,
            'pump_depth': 1400.0,  # указана явно
            'is_active': False
        }
    ]

    created = 0
    for data in wells_data:
        # Проверяем, существует ли уже скважина с таким именем
        if Well.objects.filter(name=data['name']).exists():
            print(f"⚠ Скважина '{data['name']}' уже существует, пропускаем")
            continue

        well = Well.objects.create(**data)
        created += 1
        print(f"✓ Создана скважина: {well.name} (ID: {well.id})")

        # Демонстрация расчетов
        print(f"   Макс. дебит: {well.get_max_possible_flow()} м³/сут")
        print(f"   Реком. дебит: {well.get_recommended_flow()} м³/сут")
        if well.pump_depth:
            print(f"   Глубина спуска (явно): {well.pump_depth} м")
        else:
            rec_depth = well.get_pump_depth()
            print(f"   Глубина спуска (расчет): {rec_depth} м")

        # Расчет напора для рекомендованного дебита
        rec_flow = well.get_recommended_flow()
        head = well.calculate_required_head(rec_flow)
        print(f"   Потребный напор: {head} м")
        print("-" * 50)

    print(f"\n✅ Всего создано: {created} скважин")
    print(f"📊 Всего в базе: {Well.objects.count()} скважин")


def clear_wells():
    """Очистка всех тестовых скважин (осторожно!)"""
    confirm = input("Удалить ВСЕ скважины? (yes/no): ")
    if confirm.lower() == 'yes':
        count = Well.objects.count()
        Well.objects.all().delete()
        print(f"✅ Удалено {count} скважин")
    else:
        print("❌ Операция отменена")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--clear':
        clear_wells()
    else:
        create_test_wells()