from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import logging
from django.core.management import call_command

logger = logging.getLogger(__name__)


class TelemetryScheduler:
    """Планировщик для автоматического сбора телеметрии."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Настройка задач планировщика."""

        # Сбор телеметрии каждые 120 секунд
        self.scheduler.add_job(
            func=self.fetch_all_telemetry,
            trigger=IntervalTrigger(seconds=60),
            id='fetch_telemetry',
            name='Сбор телеметрии всех скважин',
            replace_existing=True,
            misfire_grace_time=60
        )

        logger.info("Задачи планировщика настроены")

    def fetch_all_telemetry(self):
        """Запуск сбора телеметрии для всех скважин."""
        try:
            logger.info("🚀 Запуск сбора телеметрии...")

            # Вызываем нашу management команду
            call_command('fetch_telemetry')

            logger.info("✅ Сбор телеметрии завершен")
        except Exception as e:
            logger.error(f"❌ Ошибка сбора телеметрии: {e}")

    def start(self):
        """Запуск планировщика."""
        try:
            self.scheduler.start()
            logger.info("✅ Планировщик запущен")

            # Автоматическая остановка при завершении программы
            atexit.register(lambda: self.shutdown())
        except Exception as e:
            logger.error(f"❌ Ошибка запуска планировщика: {e}")

    def shutdown(self):
        """Остановка планировщика."""
        try:
            self.scheduler.shutdown()
            logger.info("⏹ Планировщик остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки планировщика: {e}")

    def get_jobs(self):
        """Получение списка задач."""
        return self.scheduler.get_jobs()


# Создаем глобальный экземпляр планировщика
scheduler = TelemetryScheduler()
