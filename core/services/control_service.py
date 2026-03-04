import requests
import logging
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from core.models import Well, CommandLog
from core.utils.validators import validate_frequency, validate_current, validate_well_id, validate_command_type

logger = logging.getLogger(__name__)


class ControlService:
    """
    Сервис для отправки команд во внешнее приложение управления станциями.
    """

    def __init__(self, api_url=None, api_key=None):
        self.api_url = api_url or getattr(settings, 'CONTROL_API_URL', 'https://api.control-system.local')
        self.api_key = api_key or getattr(settings, 'CONTROL_API_KEY', '')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def send_command(self, well_id, command_type, parameters, reason="auto", user="system"):
        """
        Отправка команды во внешнее приложение с валидацией и логированием.
        """
        # ВРЕМЕННО: возвращаем успех для всех типов команд
        command = {
            'well_id': well_id,
            'command_type': command_type,
            'parameters': parameters,
            'reason': reason,
            'user': user
        }

        print(f"Команда: {command}")

        # Логируем в БД
        try:
            well = Well.objects.get(id=well_id)
            log = CommandLog.objects.create(
                well=well,
                command_type=command_type,
                parameters=parameters,
                status='success',
                response={'message': 'Тестовый режим'}
            )
            print(f"✅ Лог сохранен ID: {log.id}")
        except Exception as e:
            print(f"Ошибка логирования: {e}")

        return {
            'status': 'success',
            'message': 'Команда принята (тестовый режим)',
            'command': command
        }
        # log = None
        # try:
        #     # Валидация
        #     validate_well_id(well_id)
        #     validate_command_type(command_type)
        #
        #     if command_type == 'frequency_adjust':
        #         validate_frequency(parameters.get('target_frequency', 0))
        #         validate_current(parameters.get('max_current', 0))
        #
        #     well = Well.objects.get(id=well_id)
        #
        #     # Формируем команду
        #     command = {
        #         "well_id": str(well.id),
        #         "command_type": command_type,
        #         "parameters": parameters,
        #         "mode": "auto" if reason != "manual" else "manual",
        #         "reason": reason
        #     }
        #
        #     # Создаем запись в логе
        #     log = CommandLog.objects.create(
        #         well=well,
        #         command_type=command_type,
        #         parameters={
        #             'command': command,
        #             'reason': reason,
        #             'user': user
        #         },
        #         status='sent'
        #     )
        #
        #     logger.info(f"Отправка команды: {command}")
        #
        #     # Отправка запроса
        #     response = requests.post(
        #         f"{self.api_url}/commands",
        #         json=command,
        #         headers=self.headers,
        #         timeout=10
        #     )
        #
        #     # Парсим ответ
        #     try:
        #         response_data = response.json()
        #     except ValueError:
        #         response_data = {
        #             'raw_response': response.text,
        #             'status_code': response.status_code
        #         }
        #
        #     # Обновляем лог
        #     if response.status_code in [200, 201, 202]:
        #         log.status = 'success'
        #         log.response = response_data
        #         log.save()
        #
        #         self._log_command(command, response.status_code, response_data)
        #
        #         return {
        #             'status': 'success',
        #             'external_response': response_data,
        #             'command': command,
        #             'log_id': log.id
        #         }
        #     else:
        #         log.status = 'error'
        #         log.response = response_data
        #         log.error_message = f"HTTP {response.status_code}: {response.text}"
        #         log.save()
        #
        #         return {
        #             'status': 'error',
        #             'code': response.status_code,
        #             'response': response_data,
        #             'log_id': log.id
        #         }
        #
        # except ValidationError as e:
        #     logger.error(f"Ошибка валидации: {e}")
        #     if log:
        #         log.status = 'error'
        #         log.error_message = str(e)
        #         log.save()
        #     return {'status': 'error', 'message': str(e)}
        #
        # except Well.DoesNotExist:
        #     logger.error(f"Скважина {well_id} не найдена")
        #     if log:
        #         log.status = 'error'
        #         log.error_message = f"Well {well_id} not found"
        #         log.save()
        #     return {'status': 'error', 'message': 'Well not found'}
        #
        # except requests.RequestException as e:
        #     logger.error(f"Ошибка соединения: {e}")
        #     if log:
        #         log.status = 'error'
        #         log.error_message = str(e)
        #         log.save()
        #     return {'status': 'error', 'message': str(e)}
        #
        # except Exception as e:
        #     logger.error(f"Неизвестная ошибка: {e}")
        #     if log:
        #         log.status = 'error'
        #         log.error_message = str(e)
        #         log.save()
        #     return {'status': 'error', 'message': str(e)}

    def _log_command(self, command, status_code, response):
        """Логирование команды для аудита."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'status_code': status_code,
            'response': response
        }
        logger.info(f"Команда выполнена: {log_entry}")

    def set_frequency(self, well_id, frequency, ramp_time=30, max_current=120.0, reason="manual", user="system"):
        """
        Установка частоты с валидацией.
        """
        parameters = {
            "target_frequency": frequency,
            "ramp_time": ramp_time,
            "max_current": max_current
        }
        return self.send_command(well_id, "frequency_adjust", parameters, reason, user)

    def emergency_stop(self, well_id, reason="emergency", user="system"):
        """
        Аварийная остановка.
        """
        return self.send_command(well_id, "emergency_stop", {}, reason, user)

    def start(self, well_id, reason="manual", user="system"):
        """
        Запуск скважины.
        """
        return self.send_command(well_id, "start", {}, reason, user)

    def stop(self, well_id, reason="manual", user="system"):
        """
        Остановка скважины.
        """
        return self.send_command(well_id, "stop", {}, reason, user)

    def calculate_optimal_frequency(self, well_id):
        """
        Расчет оптимальной частоты для скважины на основе телеметрии.
        Временная версия для тестирования.
        """
        try:
            from core.models import Well, TelemetryData

            well = Well.objects.get(id=well_id)
            latest = well.telemetry.first()

            if not latest:
                # Если нет телеметрии, возвращаем 50 Гц
                return 50.0

            # Простой алгоритм: частота = 50 Гц ± корректировка
            base_freq = 50.0

            # Корректировка по загрузке
            if latest.load_percent:
                # Если загрузка < 50%, увеличиваем частоту
                if latest.load_percent < 50:
                    return round(min(base_freq * 1.1, 60), 1)
                # Если загрузка > 90%, уменьшаем частоту
                elif latest.load_percent > 90:
                    return round(max(base_freq * 0.9, 30), 1)

            return base_freq

        except Exception as e:
            print(f"Ошибка расчета частоты: {e}")
            return 50.0
