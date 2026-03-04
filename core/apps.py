from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    # def ready(self):
    #     """Запуск при старте Django."""
    #     try:
    #         # Импортируем здесь чтобы избежать циклических импортов
    #         from .scheduler import scheduler
    #         scheduler.start()
    #         logger.info("Планировщик запущен из CoreConfig")
    #     except Exception as e:
    #         logger.error(f"Ошибка запуска планировщика: {e}")
