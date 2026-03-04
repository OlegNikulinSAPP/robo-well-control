from django.core.management.base import BaseCommand
from core.models import PumpCharacteristic, ElectricMotor


class Command(BaseCommand):
    help = 'Автоматический подбор рекомендуемых двигателей для насосов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--service-factor',
            type=float,
            default=1.5,
            help='Коэффициент запаса (по умолчанию 1.15)'
        )
        parser.add_argument(
            '--update-all',
            action='store_true',
            help='Обновить все насосы, даже если уже есть рекомендации'
        )

    def handle(self, *args, **options):
        service_factor = options['service_factor']
        update_all = options['update_all']

        pumps = PumpCharacteristic.objects.filter(is_active=True)

        updated = 0
        skipped = 0

        for pump in pumps:
            # Пропускаем если уже есть рекомендации и не forced update
            if pump.recommended_motor and not update_all:
                skipped += 1
                continue

            # Расчет требуемой мощности
            power_data = pump.calculate_power_consumption()
            required_power = power_data['shaft_power_kw'] * service_factor

            # Поиск подходящий двигателей
            motors = ElectricMotor.objects.filter(
                is_active=True,
                nominal_power__gte=required_power * 0.8,
                nominal_power__lte=required_power * 1.2
            ).order_by('-efficiency')

            if motors.exists():
                # Берем самый эффективный
                best_motor = motors.first()
                pump.recommended_motor = best_motor
                pump.save()
                updated += 1
                self.stdout.write(
                    f'{pump.harka_stupen} - {best_motor.model} '
                    f'{best_motor.nominal_power} кВт, КПД={best_motor.efficiency}%'
                )
            else:
                self.stduot.write(
                    self.style.WARNING(
                        f'{pump.harka_stupen}: нет подходящих двигателей'
                    )
                )

        self.stdout.write(
            f'\nГотово! Обновлено: {updated}, пропущено: {skipped}'
        )
