import requests
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.models import Well, TelemetryData


logger = logging.getLogger(__name__)


class TelemetryAPIClient:
    """
    Клиент для параллельного получения телеметрии скважин из внешнего API
    """
    def __init__(self, api_url=None, api_key=None, max_workers=5):
        self.api_url = 'http://62.217.179.82:1337'
        self.api_key = 'api-wellmon-8f3b1a4e-dc2f-4b8a-9c1d-4e5f6g7h8i9j'
        self.max_workers = max_workers
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _get_wells_to_poll(self):
        """Получить список активных скважин с external_id для опроса"""
        return Well.objects.filter(  # noqa
            is_active=True,
            external_id__isnull=False
        )

    def _fetch_single_well(self, well):
        """Получить телеметрию для одной скважины."""
        try:
            url = f"{self.api_url}/public-api/wells/{well.external_id}/modbus-data/"
            response = requests.get(
                url,
                headers=self.headers,
                timeout=100
            )
            if response.status_code == 200:
                data = response.json()
                print(f"ТИП: {type(data)}")
                print(f"КЛЮЧИ: {data.keys() if isinstance(data, dict) else 'ЭТО СПИСОК'}")
                return self._save_telemetry(data, well)
            return None

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут при запросе скважины {well.external_id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при запросе скважины {well.external_id}: {e}")
            return None

    def fetch_all_wells_parallel(self):
        """Параллельный сбор телеметрии со всех активных скважин."""
        results = {'success': [], 'failed': []}

        print(f"🔥 Тип self в fetch_all_wells_parallel: {type(self)}")
        print(f"🔥 self.__dict__: {self.__dict__}")

        wells = self._get_wells_to_poll()

        if not wells:
            logger.warning("Нет активных скважин для опроса")
            return results

        logger.info(f"Начинаю параллельный опрос {len(wells)} скважин, воркеров: {self.max_workers}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_well = {
                executor.submit(self._fetch_single_well, well): well
                for well in wells
            }

            for future in as_completed(future_to_well):
                well = future_to_well[future]
                try:
                    result = future.result(timeout=5)
                    if result:
                        results['success'].append(well.external_id)
                    else:
                        results['failed'].append(well.external_id)
                except Exception as e:
                    logger.error(f"Ошибка при обработке результата для скважины {well.external_id}: {e}")
                    results['failed'].append(well.external_id)

        logger.info(f"Опрос завершен. Успешно: {len(results['success'])}, Ошибок: {len(results['failed'])}")
        return results

    def _save_telemetry(self, data, well):
        try:
            print(f"💾 СОХРАНЕНИЕ для скважины {well.external_id}")

            if 'data' in data:
                telemetry_data = data['data']
            else:
                telemetry_data = data

            parsed = self.parse_telemetry(telemetry_data, well.id)
            print(f"📝 parsed timestamp: {parsed['timestamp']}")

            telemetry = TelemetryData.objects.create(
                well=well,
                external_id=str(well.id),
                timestamp=datetime.fromisoformat(parsed['timestamp']),
                current_phase_a=parsed.get('current_phase_a'),
                current_phase_b=parsed.get('current_phase_b'),
                current_phase_c=parsed.get('current_phase_c'),
                active_power=parsed.get('active_power'),
                frequency=parsed.get('frequency'),
                intake_pressure=parsed.get('intake_pressure'),
                intake_temperature=parsed.get('intake_temperature'),
                motor_temperature=parsed.get('motor_temperature'),
                vibration_x=parsed.get('vibration_x'),
                vibration_y=parsed.get('vibration_y'),
                raw_data=data
            )

            print(f"✅ СОХРАНЕНО! ID={telemetry.id}, timestamp={telemetry.timestamp}")
            print(f"   давление={telemetry.intake_pressure}, температура={telemetry.intake_temperature}")

            from core.services.alert_service import AlertService
            AlertService.check_telemetry(telemetry)

            return True

        except Exception as e:
            print(f"❌ ОШИБКА СОХРАНЕНИЯ: {e}")
            logger.error(f"Ошибка сохранения телеметрии для скважины {well.external_id}: {e}")
            return False

    def parse_telemetry(self, data, well_id):
        """Преобразовать сырые данные API в структурированный словарь."""
        result = {
            'well_id': well_id,
            'timestamp': datetime.now().isoformat(),
            'current_phase_a': None,
            'current_phase_b': None,
            'current_phase_c': None,
            'active_power': None,
            'intake_pressure': None,
            'intake_temperature': None,
            'motor_temperature': None,
            'vibration_x': None,
            'vibration_y': None,
            'frequency': None,
        }

        if 'input_registers' not in data:
            return result

        reg_data = data['input_registers']

        # Словарь соответствий: ключ в API -> (поле в result, множитель)
        mapping = {
            'Полный ток двигателя фазы А': ('current_phase_a', 0.1),
            'Полный ток двигателя фазы B': ('current_phase_b', 0.1),
            'Полный ток двигателя фазы C': ('current_phase_c', 0.1),
            'Активная мощность': ('active_power', 0.1),
            'Давление на приеме насоса': ('intake_pressure', 0.01),  # особый случай, позже пересчитаем
            'Температура жидкости на приеме насоса': ('intake_temperature', 0.01),
            'Температура двигателя': ('motor_temperature', 0.01),
            'Вибрация по оси X': ('vibration_x', 1),
            'Вибрация по оси Y': ('vibration_y', 1),
            'Частота питания ПЭД': ('frequency', 0.01),
        }

        for api_key, (result_field, multiplier) in mapping.items():
            if api_key in reg_data:
                raw_value = reg_data[api_key]['raw_value']
                value = raw_value * multiplier

                # Особая обработка для давления (перевод из МПа в атм)
                if api_key == 'Давление на приеме насоса':
                    value = round(value * 9.87, 2)  # МПа → атм

                result[result_field] = value

        return result
