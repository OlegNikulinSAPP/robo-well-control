from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Запуск планировщика при старте Django."""
        # Временно отключаем для отладки
        # try:
        #     from .scheduler import scheduler
        #     scheduler.start()
        #     logger.info("Планировщик автоматически запущен при старте Django")
        # except Exception as e:
        #     logger.error(f"Ошибка запуска планировщика: {e}")
        pass
