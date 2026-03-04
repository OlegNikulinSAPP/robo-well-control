import requests
import logging
from datetime import datetime
from django.conf import settings
from core.models import Well, TelemetryData
from core.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class TelemetryAPIClient:
    """
    Клиент для получения телеметрии скважин из внешнего API.
    """

    def __init__(self, api_url=None, api_key=None):
        self.api_url = 'http://62.217.179.82:1337'
        self.api_key = 'api-wellmon-8f3b1a4e-dc2f-4b8a-9c1d-4e5f6g7h8i9j'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def fetch_well_telemetry(self, well_id):
        """
        Получение телеметрии для одной скважины.
        """
        try:
            url = f"{self.api_url}/public-api/wells/{well_id}/modbus-data/"
            print(f"Отправка запроса: {url}")

            response = requests.get(
                url,
                headers=self.headers,
                timeout=100
            )

            print(f"Статус ответа: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("УСПЕХ! Данные получены")
                print(f"Тип data: {type(data)}")
                for i in data:
                    print(i)

                return self.save_telemetry(data, well_id)
            else:
                print(f"Ошибка API: {response.status_code}")
                return None

        except Exception as e:
            print(f"Ошибка запроса: {e}")
            return None

    def fetch_all_wells(self):
        """
        Получение телеметрии для всех скважин из БД.
        """
        results = {'success': [], 'failed': []}

        # Берем все скважины из нашей БД
        wells = Well.objects.all()

        for well in wells:
            if hasattr(well, 'external_id') and well.external_id:
                result = self.fetch_well_telemetry(well.external_id)
                if result:
                    results['success'].append(well.external_id)
                else:
                    results['failed'].append(well.external_id)

        return results

    def parse_telemetry(self, data, well_id):
        """
        Парсинг данных телеметрии.
        data - словарь с полями coils, input_statuses, holding_registers, input_registers
        """
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

        # Парсим input_registers (измерения)
        if 'input_registers' in data:
            reg_data = data['input_registers']
            # Токи (адреса 4-6 - полный ток фаз)
            if 'Полный ток двигателя фазы А' in reg_data:
                result['current_phase_a'] = reg_data['Полный ток двигателя фазы А']['raw_value'] * 0.1
            if 'Полный ток двигателя фазы B' in reg_data:
                result['current_phase_b'] = reg_data['Полный ток двигателя фазы B']['raw_value'] * 0.1
            if 'Полный ток двигателя фазы C' in reg_data:
                result['current_phase_c'] = reg_data['Полный ток двигателя фазы C']['raw_value'] * 0.1

            # Мощность
            if 'Активная мощность' in reg_data:
                result['active_power'] = reg_data['Активная мощность']['raw_value'] * 0.1

            # Давление на приеме (адрес 122)
            if 'Давление на приеме насоса' in reg_data:
                mpa = reg_data['Давление на приеме насоса']['raw_value'] * 0.01
                result['intake_pressure'] = round(mpa * 9.87, 2)

            # Температуры
            if 'Температура жидкости на приеме насоса' in reg_data:
                result['intake_temperature'] = reg_data['Температура жидкости на приеме насоса']['raw_value'] * 0.01
            if 'Температура двигателя' in reg_data:
                result['motor_temperature'] = reg_data['Температура двигателя']['raw_value'] * 0.01

            # Вибрация
            if 'Вибрация по оси X' in reg_data:
                result['vibration_x'] = reg_data['Вибрация по оси X']['raw_value']
            if 'Вибрация по оси Y' in reg_data:
                result['vibration_y'] = reg_data['Вибрация по оси Y']['raw_value']

            # Частота (адрес 56)
            if 'Частота питания ПЭД' in reg_data:
                result['frequency'] = reg_data['Частота питания ПЭД']['raw_value'] * 0.01

        return result

    def save_telemetry(self, data, well_id):
        """
        Сохранение телеметрии в БД.
        """
        # Извлекаем внутренние данные из обертки
        if 'data' in data:
            telemetry_data = data['data']
        else:
            telemetry_data = data

        parsed = self.parse_telemetry(telemetry_data, well_id)
        print(f"Распарсено: {parsed}")

        try:
            well = Well.objects.get(id=well_id)
            print(f"Найдена скважина: {well.name}")

            telemetry = TelemetryData.objects.create(
                well=well,
                external_id=str(well_id),
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
            print(f"\n✅ СОХРАНЕНА ЗАПИСЬ ID: {telemetry.id}")
            print(f"   Давление: {telemetry.intake_pressure}")
            print(f"   Температура: {telemetry.intake_temperature}")
            print(f"   Ток A: {telemetry.current_phase_a}")
            print(f"   Вибрация X: {telemetry.vibration_x}\n")

            return True

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
