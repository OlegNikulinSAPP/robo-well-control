from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
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
        """Настройка задач."""

        # Задача 1: Сбор телеметрии каждые 30 секунд
        self.scheduler.add_job(
            func=self.fetch_all_telemetry,
            trigger=IntervalTrigger(seconds=120),
            id='fetch_telemetry_30s',
            name='Сбор телеметрии всех скважин',
            replace_existing=True,
            misfire_grace_time=120
        )

        # Задача 2: Проверка уставок каждую минуту
        self.scheduler.add_job(
            func=self.check_alerts,
            trigger=IntervalTrigger(seconds=160),
            id='check_alerts_60s',
            name='Проверка уставок',
            replace_existing=True
        )

        logger.info("Задачи планировщика настроены")

    def fetch_all_telemetry(self):
        """Запуск сбора телеметрии для всех скважин."""
        try:
            logger.info("Запуск сбора телеметрии...")
            # call_command('fetch_telemetry')
            call_command('fetch_telemetry', '--well-id', '1')
            logger.info("Сбор телеметрии завершен")
        except Exception as e:
            logger.error(f"Ошибка сбора телеметрии: {e}")

    def check_alerts(self):
        """Проверка уставок и создание уведомлений."""
        try:
            from core.services.alert_service import AlertService
            alerts = AlertService.check_all_wells()
            if alerts:
                logger.info(f"Создано {len(alerts)} уведомлений")
        except Exception as e:
            logger.error(f"Ошибка проверки уставок: {e}")

    def start(self):
        """Запуск планировщика."""
        try:
            self.scheduler.start()
            logger.info("Планировщик запущен")

            # Остановка при завершении
            atexit.register(lambda: self.shutdown())
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")

    def shutdown(self):
        """Остановка планировщика."""
        try:
            self.scheduler.shutdown()
            logger.info("Планировщик остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки планировщика: {e}")

    def get_jobs(self):
        """Получение списка задач."""
        return self.scheduler.get_jobs()


# Создаем глобальный экземпляр
scheduler = TelemetryScheduler()