import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import PumpCharacteristic


class Command(BaseCommand):
    """
    Команда Django для импорта характеристик насосов из Excel.

    Использование:
    python manage.py import_pumps /путь/к/файлу.xlsx
    python manage.py import_pumps /путь/к/папке --folder
    """
    help = 'Импорт характеристик насосов ЭЦН из Excel файлов'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            type=str,
            help='Путь к Excel файлу или папке с файлами'
        )
        parser.add_argument(
            '--folder',
            action='store_true',
            help='Импортировать все Excel файлы из папки'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить существующие записи'
        )

    def handle(self, *args, **options):
        path = options['path']
        is_folder = options['folder']
        update_existing = options['update']

        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Путь не найден: {path}"))
            return

        if is_folder:
            self.import_folder(path, update_existing)
        else:
            self.import_file(path, update_existing)

    def import_folder(self, folder_path, update_existing):
        """
        Импорт всех Excel файлов из папки.

        Args:
            folder_path: Путь к папке
            update_existing: Обновлять существующие записи
        """
        excel_files = []

        for file_name in os.listdir(folder_path):
            if file_name.endswith(('.xlsx', '.xls')):
                excel_files.append(os.path.join(folder_path, file_name))

        self.stdout.write(f"Найдено {len(excel_files)} Excel файлов")

        total_success = 0
        total_errors = 0

        for file_path in excel_files:
            success, errors = self.import_file(file_path, update_existing)
            total_success += success
            total_errors += errors

        self.stdout.write(self.style.SUCCESS(
            f"Импорт папки завершен. Успешно: {total_success}, Ошибок: {total_errors}"
        ))

    def import_file(self, file_path, update_existing):
        """
        Импорт одного Excel файла.

        Args:
            file_path: Путь к Excel файлу
            update_existing: Обновлять существующие записи

        Returns:
            tuple: (success_count, error_count)
        """
        self.stdout.write(f"Импорт файла: {os.path.basename(file_path)}")

        try:
            df = self.load_excel_file(file_path)
            if df is None:
                return 0, 1

            pumps_data = self.parse_dataframe(df, file_path)
            success, errors = self.save_to_database(pumps_data, update_existing)

            self.stdout.write(self.style.SUCCESS(
                f"  Успешно: {success}, Ошибок: {errors}"
            ))

            return success, errors

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Ошибка импорта: {e}"))
            return 0, 1

    def load_excel_file(self, file_path):
        """
        Загрузка Excel файла в DataFrame.

        Args:
            file_path: Путь к файлу

        Returns:
            DataFrame или None
        """
        try:
            # Пробуем разные кодировки и параметры
            df = pd.read_excel(
                file_path,
                sheet_name=0,
                dtype={'cod': str}  # Код как строка для безопасности
            )
            return df
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Ошибка чтения Excel: {e}"))
            return None

    def parse_dataframe(self, df, file_path):
        """
        Парсинг DataFrame с данными насосов.

        Args:
            df: DataFrame с данными
            file_path: Путь к исходному файлу

        Returns:
            list: Список словарей с данными насосов
        """
        pumps_data = []
        file_name = os.path.basename(file_path)

        for index, row in df.iterrows():
            try:
                pump_data = self.parse_row(row, file_name)
                if pump_data:
                    pumps_data.append(pump_data)

            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  Ошибка в строке {index + 2}: {e}"
                ))

        self.stdout.write(f"  Найдено {len(pumps_data)} насосов в файле")
        return pumps_data

    def parse_row(self, row, file_name):
        """
        Парсинг одной строки DataFrame.

        Args:
            row: Строка DataFrame
            file_name: Имя файла

        Returns:
            dict: Данные насоса
        """
        # Проверяем обязательные поля
        required_fields = ['cod', 'harka_stupen']
        for field in required_fields:
            if field not in row or pd.isna(row[field]):
                return None

        pump_data = {
            'cod': int(float(row['cod'])) if not pd.isna(row['cod']) else 0,
            'zavod': str(row.get('Zavod', 'ESP')).strip(),
            'harka_stupen': str(row['harka_stupen']).strip(),
            'material_stupen': str(row.get('material_stupen', '')).strip(),
            'source_file': file_name,
        }

        # Парсим массивы значений
        pump_data['q_values'] = self.parse_value_string(row.get('Q', ''))
        pump_data['h_values'] = self.parse_value_string(row.get('H', ''))
        pump_data['n_values'] = self.parse_value_string(row.get('N', ''))
        pump_data['kpd_values'] = self.parse_value_string(row.get('KPD', ''))

        # Парсим диапазоны
        pump_data['left_range'] = float(row.get('Left', 0))
        pump_data['nominal_range'] = float(row.get('Nominal', 0))
        pump_data['right_range'] = float(row.get('Right', 0))

        # Минимальный КПД
        min_kpd = row.get('minKPDROSNEFT', 25.0)
        pump_data['min_kpd_rosneft'] = float(min_kpd) if pd.notna(min_kpd) else 25.0

        return pump_data

    def parse_value_string(self, value):
        """
        Парсинг строки с массивами значений.

        Args:
            value: Значение из ячейки

        Returns:
            list: Список чисел
        """
        if pd.isna(value):
            return []

        str_value = str(value)
        values = []

        # Разные форматы разделителей
        for part in str_value.replace(',', ' ').split():
            try:
                # Заменяем запятые на точки и убираем лишние символы
                cleaned = part.strip().replace(',', '.')
                if cleaned:
                    values.append(float(cleaned))
            except ValueError:
                continue

        return values

    def save_to_database(self, pumps_data, update_existing):
        """
        Сохранение данных в базу.

        Args:
            pumps_data: Список данных насосов
            update_existing: Обновлять существующие записи

        Returns:
            tuple: (success_count, error_count)
        """
        success = 0
        errors = 0

        with transaction.atomic():
            for pump_data in pumps_data:
                try:
                    if update_existing:
                        # Обновление существующей записи
                        characteristic, created = PumpCharacteristic.objects.update_or_create(
                            cod=pump_data['cod'],
                            harka_stupen=pump_data['harka_stupen'],
                            source_file=pump_data['source_file'],
                            defaults=pump_data
                        )
                        action = "обновлен" if not created else "создан"
                    else:
                        # Только создание новых
                        if PumpCharacteristic.objects.filter(
                                cod=pump_data['cod'],
                                harka_stupen=pump_data['harka_stupen']
                        ).exists():
                            self.stdout.write(self.style.WARNING(
                                f"  Насос {pump_data['harka_stupen']} уже существует, пропускаем"
                            ))
                            continue

                        characteristic = PumpCharacteristic.objects.create(**pump_data)
                        action = "создан"

                    success += 1
                    self.stdout.write(f"    {characteristic} - {action}")

                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(
                        f"    Ошибка сохранения {pump_data.get('harka_stupen', 'N/A')}: {e}"
                    ))

        return success, errors