import pandas as pd
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ElectricMotor


class Command(BaseCommand):
    """
    Команда Django для импорта электродвигателей из Excel.

    Ожидает Excel файл со следующими столбцами:
    ID, Model, Power_nom, U_nom, I_nom, Turning, TurningMoment,
    R_ColdWinding, BoringMoment, U_accel, I_Idling, P_HeatedWaste,
    U_InsulWinding, U_MinInsulWinding, Time_RunDown, VibrLevel,
    U_Idling, R_Insul, P_h_h, I_k_z, U_k_z, dR_ColdWinding,
    Manufactured, P_k_z, S_load, Powerfactor_load, Efficiency_load

    Игнорируемые столбцы: I_h_h, U_k_z_0, P_k_z_0, I_load, M_Power_load
    """
    help = 'Импорт электродвигателей из Excel файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Путь к Excel файлу с данными двигателей'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить существующие записи'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Название листа в Excel (по умолчанию первый лист)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        update_existing = options['update']
        sheet_name = options['sheet']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"Файл не найден: {file_path}"))
            return

        try:
            # Загружаем Excel файл
            self.stdout.write(f"Загрузка файла: {os.path.basename(file_path)}")
            df = self.load_excel_file(file_path, sheet_name)

            if df is None:
                return

            # Парсим данные
            motors_data = self.parse_dataframe(df, file_path)

            # Сохраняем в базу
            success, errors = self.save_to_database(motors_data, update_existing)

            self.stdout.write(self.style.SUCCESS(
                f"Импорт завершен. Успешно: {success}, Ошибок: {errors}"
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка импорта: {e}"))

    def load_excel_file(self, file_path, sheet_name):
        """
        Загрузка Excel файла.

        Args:
            file_path: Путь к файлу
            sheet_name: Название листа

        Returns:
            DataFrame или None
        """
        try:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                dtype={'ID': str, 'Model': str}  # ID и Model как строки
            )
            self.stdout.write(f"  Загружено строк: {len(df)}")
            self.stdout.write(f"  Столбцы: {', '.join(df.columns)}")
            return df
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Ошибка чтения Excel: {e}"))
            return None

    def parse_dataframe(self, df, file_path):
        """
        Парсинг DataFrame.

        Args:
            df: DataFrame с данными
            file_path: Путь к файлу

        Returns:
            list: Список словарей с данными двигателей
        """
        motors_data = []
        file_name = os.path.basename(file_path)

        for index, row in df.iterrows():
            try:
                motor_data = self.parse_row(row, file_name)
                if motor_data:
                    motors_data.append(motor_data)

            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  Ошибка в строке {index + 2}: {e}"
                ))

        self.stdout.write(f"  Успешно распарсено: {len(motors_data)} двигателей")
        return motors_data

    def parse_row(self, row, file_name):
        """
        Парсинг одной строки.

        Args:
            row: Строка DataFrame
            file_name: Имя файла

        Returns:
            dict: Данные двигателя
        """
        # Проверяем обязательные поля
        required_fields = ['ID', 'Model', 'Power_nom', 'U_nom', 'I_nom']
        for field in required_fields:
            if field not in row or pd.isna(row[field]):
                self.stdout.write(f"  Пропуск строки: отсутствует поле {field}")
                return None

        # Основные данные
        motor_data = {
            'motor_id': str(row['ID']).strip(),
            'model': str(row['Model']).strip(),
        }

        # Номинальные параметры
        motor_data['nominal_power'] = self.parse_float(row.get('Power_nom'))
        motor_data['nominal_voltage'] = self.parse_float(row.get('U_nom'))
        motor_data['nominal_current'] = self.parse_float(row.get('I_nom'))

        # Механические характеристики
        motor_data['rotation_speed'] = self.parse_float(row.get('Turning'))
        motor_data['torque'] = self.parse_float(row.get('TurningMoment'))
        motor_data['shaft_torque'] = self.parse_float(row.get('BoringMoment'))

        # Электрические сопротивления
        motor_data['cold_winding_resistance'] = self.parse_float(row.get('R_ColdWinding'))
        motor_data['cold_winding_resistance_delta'] = self.parse_float(row.get('dR_ColdWinding'))

        # Пусковые характеристики
        motor_data['acceleration_voltage'] = self.parse_float(row.get('U_accel'))
        motor_data['idle_current'] = self.parse_float(row.get('I_Idling'))

        # Потери
        motor_data['heated_waste'] = self.parse_float(row.get('P_HeatedWaste'))
        motor_data['idle_losses'] = self.parse_float(row.get('P_h_h'))

        # Испытания изоляции
        motor_data['insulation_test_voltage'] = self.parse_float(row.get('U_InsulWinding'))
        motor_data['interturn_test_voltage'] = self.parse_float(row.get('U_MinInsulWinding'))
        motor_data['insulation_resistance'] = self.parse_float(row.get('R_Insul'))

        # Динамические характеристики
        motor_data['rundown_time'] = self.parse_float(row.get('Time_RunDown'))
        motor_data['vibration_level'] = self.parse_float(row.get('VibrLevel'))
        motor_data['idle_voltage'] = self.parse_float(row.get('U_Idling'))

        # Параметры короткого замыкания
        motor_data['short_circuit_current'] = self.parse_float(row.get('I_k_z'))
        motor_data['short_circuit_voltage'] = self.parse_float(row.get('U_k_z'))
        motor_data['short_circuit_power'] = self.parse_float(row.get('P_k_z'))

        # Производитель
        motor_data['manufacturer'] = str(row.get('Manufactured', 'Неизвестно')).strip()

        # Рабочие параметры
        motor_data['slip'] = self.parse_float(row.get('S_load'))
        motor_data['power_factor'] = self.parse_float(row.get('Powerfactor_load'))
        motor_data['efficiency'] = self.parse_float(row.get('Efficiency_load'))

        # Добавляем источник
        motor_data['source_file'] = file_name

        return motor_data

    def parse_float(self, value):
        """
        Безопасное преобразование в float.

        Args:
            value: Значение для преобразования

        Returns:
            float: Преобразованное значение или 0.0
        """
        if pd.isna(value):
            return 0.0

        try:
            # Заменяем запятые на точки и убираем лишние символы
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
                # Убираем нечисловые символы в конце
                while value and not value[-1].isdigit():
                    value = value[:-1]

            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def save_to_database(self, motors_data, update_existing):
        """
        Сохранение данных в базу.

        Args:
            motors_data: Список данных двигателей
            update_existing: Обновлять существующие

        Returns:
            tuple: (success_count, error_count)
        """
        success = 0
        errors = 0

        with transaction.atomic():
            for motor_data in motors_data:
                try:
                    if update_existing:
                        # Обновление существующей записи
                        motor, created = ElectricMotor.objects.update_or_create(
                            motor_id=motor_data['motor_id'],
                            defaults=motor_data
                        )
                        action = "обновлен" if not created else "создан"
                    else:
                        # Только создание новых
                        if ElectricMotor.objects.filter(motor_id=motor_data['motor_id']).exists():
                            self.stdout.write(f"  Двигатель {motor_data['motor_id']} уже существует, пропускаем")
                            continue

                        motor = ElectricMotor.objects.create(**motor_data)
                        action = "создан"

                    success += 1
                    self.stdout.write(f"    {motor.model} (ID: {motor.motor_id}) - {action}")

                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(
                        f"    Ошибка сохранения {motor_data.get('model', 'N/A')}: {e}"
                    ))

        return success, errors