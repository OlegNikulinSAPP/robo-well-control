# core/management/commands/recalculate_pumps.py
from django.core.management.base import BaseCommand
from core.models import PumpCharacteristic


class Command(BaseCommand):
    help = 'Пересчет оптимальных диапазонов по новой логике (75% от max КПД)'

    def handle(self, *args, **options):
        pumps = PumpCharacteristic.objects.all()

        for pump in pumps:
            self.stdout.write(f"Обработка: {pump.harka_stupen}")

            # Сбрасываем оптимальный диапазон
            pump.optimal_flow_range = []
            pump.max_efficiency = None
            pump.max_efficiency_flow = None

            if pump.kpd_values and pump.q_values:
                # Находим максимальный КПД
                max_kpd = max(pump.kpd_values)
                max_idx = pump.kpd_values.index(max_kpd)

                pump.max_efficiency = max_kpd
                pump.max_efficiency_flow = pump.q_values[max_idx]

                # 75% от максимального КПД
                threshold_kpd = max_kpd * 0.75

                # Ищем диапазон
                start_idx = None
                end_idx = None

                # Левая граница
                for i in range(max_idx, -1, -1):
                    if pump.kpd_values[i] >= threshold_kpd:
                        start_idx = i
                    else:
                        break

                # Правая граница
                for i in range(max_idx, len(pump.kpd_values)):
                    if pump.kpd_values[i] >= threshold_kpd:
                        end_idx = i
                    else:
                        break

                if start_idx is not None and end_idx is not None:
                    pump.optimal_flow_range = [
                        pump.q_values[start_idx],
                        pump.q_values[end_idx]
                    ]
                    self.stdout.write(
                        f"  Оптимальный: {pump.optimal_flow_range} "
                        f"(max КПД={max_kpd}% при Q={pump.q_values[max_idx]})"
                    )
                else:
                    pump.optimal_flow_range = [pump.left_range, pump.right_range]
                    self.stdout.write(f"  Рабочий: {pump.optimal_flow_range}")

            pump.save()

        self.stdout.write(self.style.SUCCESS(
            f"Готово! Пересчитано {pumps.count()} насосов"
        ))