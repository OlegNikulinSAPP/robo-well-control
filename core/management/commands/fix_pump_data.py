# core/management/commands/fix_pump_data.py
from django.core.management.base import BaseCommand
from core.models import PumpCharacteristic


class Command(BaseCommand):
    help = 'Принудительный пересчет всех полей насосов'

    def handle(self, *args, **options):
        pumps = PumpCharacteristic.objects.all()

        for pump in pumps:
            self.stdout.write(f"Обработка: {pump.harka_stupen}")

            # Принудительно вызываем save() с пересчетом
            pump.save()

            self.stdout.write(f"  Max КПД: {pump.max_efficiency}% при Q={pump.max_efficiency_flow}")
            self.stdout.write(f"  Оптимальный диапазон: {pump.optimal_flow_range}")

        self.stdout.write(self.style.SUCCESS(
            f"Готово! Обработано {pumps.count()} насосов"
        ))