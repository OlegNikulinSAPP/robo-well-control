from django.core.management.base import BaseCommand
from core.services.telemetry_api import TelemetryAPIClient
import logging
# from core.models import Well

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Параллельный сбор телеметрии со всех скважин'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=5,
            help='Количество параллельных потоков (по умолчанию 5)'
        )
        parser.add_argument(
            '--well-id',
            type=int,
            help='ID конкретной скважины для опроса (если не указан - опрашиваются все)'
        )

    def handle(self, *args, **options):
        workers = options.get('workers', 5)
        well_id = options.get('well_id')

        self.stdout.write(f"🚀 Запуск сбора телеметрии (воркеров: {workers})")

        client = TelemetryAPIClient(max_workers=workers)

        # Если запрошена конкретная скважина
        if well_id:
            from core.models import Well
            try:
                well = Well.objects.get(id=well_id)
            except Well.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Скважина с ID {well_id} не найдена"))
                return

            self.stdout.write(f"📡 Опрос скважины {well.name} (ID: {well.id})...")
            result = client._fetch_single_well(well)

            if result:
                self.stdout.write(self.style.SUCCESS(f"✅ Данные для скважины {well.name} получены и сохранены"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Не удалось получить данные для скважины {well.name}"))
            return

        # Если опрашиваем все скважины
        try:
            results = client.fetch_all_wells_parallel()
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Готово! Успешно: {len(results['success'])}, Ошибок: {len(results['failed'])}"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Критическая ошибка: {e}"))
            logger.error(f"Ошибка в команде fetch_telemetry: {e}", exc_info=True)
