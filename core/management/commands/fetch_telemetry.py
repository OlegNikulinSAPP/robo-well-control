from django.core.management.base import BaseCommand
from core.services.telemetry_api import TelemetryAPIClient
from core.models import Well


class Command(BaseCommand):
    help = 'Получение телеметрии скважин из внешнего API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--well-id',
            type=int,
            help='ID скважины в нашей БД'
        )

    def handle(self, *args, **options):
        client = TelemetryAPIClient()

        if options['well_id']:
            well_id = options['well_id']
            try:
                well = Well.objects.get(id=well_id)
                self.stdout.write(f"Получение данных для скважины {well.name} (ID: {well_id})...")
                result = client.fetch_well_telemetry(well_id)  # Передаем well_id, не external_id
                if result:
                    self.stdout.write(self.style.SUCCESS("Данные получены и сохранены"))
                else:
                    self.stdout.write(self.style.ERROR("Не удалось получить данные"))
            except Well.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Скважина {well_id} не найдена"))
        else:
            self.stdout.write("Получение данных для всех скважин...")
            results = client.fetch_all_wells()
            self.stdout.write(self.style.SUCCESS(
                f"Успешно: {len(results['success'])}, Ошибок: {len(results['failed'])}"
            ))
