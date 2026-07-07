# **ПАМЯТКА**

## **ЧТО МЫ ДЕЛАЕМ?**
Создаем систему управления нефтяными скважинами на Python. Это серьезный промышленный проект, но начинаем с основ.

## **ШАГИ КОТОРЫЕ МЫ УЖЕ СДЕЛАЛИ:**

### **1. ОТКРЫЛИ PYCHARM И СОЗДАЛИ ПРОЕКТ**
- Запустили PyCharm
- Нажали "New Project" (Новый проект)
- В поле "Location" (Расположение) написали: `C:\Users\ВАШЕ_ИМЯ\PycharmProjects\robo-well-control`
  *Замените ВАШЕ_ИМЯ на ваше имя пользователя Windows*
- В разделе "Python Interpreter" выбрали "New Virtual Environment"
- Нажали "Create" (Создать)

**Что получили:** Папка проекта и виртуальное окружение (.venv)

### **2. СОЗДАЛИ ВАЖНЫЕ ФАЙЛЫ**
В терминале PyCharm (внизу экрана) выполнили:

```bash
type nul > requirements.txt
type nul > .env.example
type nul > .gitignore
type nul > docker-compose.yml
type nul > Dockerfile
type nul > README.md
```

**Объяснение команды:**
- `type nul >` - Windows-команда создать пустой файл
- `requirements.txt` - список библиотек Python для установки
- `.env.example` - шаблон для настроек (пароли, ключи)
- `.gitignore` - что НЕ загружать в GitHub
- Остальные файлы для Docker и документации

### **3. НАСТРОИЛИ .gitignore**
Открыли файл `.gitignore` и добавили:

```gitignore
.venv/          # Игнорируем виртуальное окружение
.env            # Игнорируем файл с паролями
__pycache__/    # Игнорируем кеш Python
```

**Почему .env.example а не .env?**
- `.env.example` - ШАБЛОН (без паролей) - МОЖНО загружать в GitHub
- `.env` - РЕАЛЬНЫЕ пароли - НЕЛЬЗЯ загружать в GitHub
- Поэтому `.env` в `.gitignore`

### **4. ДОБАВИЛИ БИБЛИОТЕКИ**
В файл `requirements.txt` добавили:
```
Django==4.2.11
djangorestframework==3.14.0
```

### **5. УСТАНОВИЛИ БИБЛИОТЕКИ**
В терминале выполнили:
```bash
pip install -r requirements.txt
```

**Что происходит:** Устанавливаются Django и DRF в ваше виртуальное окружение

### **6. СОЗДАЛИ DJANGO ПРОЕКТ**
В терминале выполнили:
```bash
django-admin startproject config .
```

**Что создалось:**
- `manage.py` - главный файл для управления проектом
- Папка `config/` с настройками Django

### **7. ПРОВЕРИЛИ ЧТО ВСЕ РАБОТАЕТ**
В терминале выполнили:
```bash
python manage.py runserver
```

**Что делать дальше:**
1. Открыть браузер
2. Перейти по адресу: `http://127.0.0.1:8000/`
3. Увидеть сообщение "The install worked successfully!"

## **ВАЖНЫЕ ВОПРОСЫ И ОТВЕТЫ:**

### **Где находятся файлы?**
```
C:\Users\ВАШЕ_ИМЯ\PycharmProjects\robo-well-control\
├── .venv\                    ← Виртуальное окружение Python
├── config\                   ← Настройки Django
├── .gitignore               ← Что игнорировать для GitHub
├── requirements.txt         ← Список библиотек
├── manage.py               ← Управление Django
└── .env.example            ← Шаблон настроек
```

### **Что такое виртуальное окружение (.venv)?**
Это "изолированная коробка" для Python:
- Библиотеки устанавливаются ТОЛЬКО сюда
- Не влияет на другие проекты
- Все зависимости в одном месте

### **Как работать в терминале PyCharm?**
1. Внизу экрана есть вкладка "Terminal"
2. Там уже активировано виртуальное окружение (видно `(.venv)` в начале строки)
3. Все команды выполняете там

### **Если сервер запущен, как его остановить?**
В терминале нажмите: `Ctrl + C`

### **Как проверить что все работает?**
1. Запустите: `python manage.py runserver`
2. Откройте браузер на `http://127.0.0.1:8000/`
3. Должна быть страница Django

# **ПАМЯТКА: RoboWell Control System (шаги 9-25)**

## **ЧТО МЫ СДЕЛАЛИ ПОСЛЕ ПЕРВОЙ ПАМЯТКИ:**

### **РАЗРАБОТКА МОДЕЛЕЙ:**

#### **9. Создали Django приложение "core":**
```bash
python manage.py startapp core
```
**Что это:** Отдельное приложение для основной логики системы

#### **10. Зарегистрировали приложение в Django:**
Файл `config/settings.py` → `INSTALLED_APPS` добавили:
```python
'core',
'rest_framework',
```

#### **11-15. Создали модель "Well" (Скважина):**
Файл `core/models.py`:
```python
class Well(models.Model):
    """Модель добывающей скважины."""
    name = models.CharField(...)          # Название
    depth = models.FloatField(...)       # Глубина, м
    diameter = models.FloatField(...)    # Диаметр, мм
    pump_depth = models.FloatField(...)  # Глубина насоса, м
    # ... и другие поля из ТЗ
```

**Лучшие практики которые применили:**
- ✅ **Docstring** для класса и методов
- ✅ **verbose_name** - человекочитаемые названия
- ✅ **help_text** - подсказки для пользователей
- ✅ **created_at/updated_at** - автоматические метки времени
- ✅ **Класс Meta** с настройками
- ✅ **Метод __str__** для красивого отображения

### **РАБОТА С БАЗОЙ ДАННЫХ:**

#### **16. Создали миграции:**
```bash
python manage.py makemigrations core
```
**Что делает:** Создает инструкции для создания таблицы в базе

#### **17. Применили миграции:**
```bash
python manage.py migrate
```
**Что делает:** Создает реальную таблицу в SQLite базе `db.sqlite3`

### **РАБОТА С GIT И GITHUB:**

#### **18-21. Локальные коммиты:**
```bash
git init                    # Инициализация (если не было)
git add .                  # Добавить все файлы
git commit -m "сообщение"  # Создать коммит
```

#### **22. Проверка истории:**
```bash
git log --oneline          # Краткая история коммитов
```

#### **24. Привязка к GitHub:**
```bash
git remote add origin https://github.com/ВАШ_ЛОГИН/robo-well-control.git
```

#### **25. Отправка на GitHub (PUSH):**
```bash
git push -u origin master
```
**Флаг `-u`** запоминает связь, чтобы в будущем писать просто `git push`

## **ВАЖНЫЕ КОНЦЕПЦИИ:**

### **1. Миграции в Django:**
- **makemigrations** - создать инструкции
- **migrate** - выполнить инструкции
- Миграции хранятся в `core/migrations/`

### **2. Модели Django:**
- Описывают структуру таблиц в базе
- Автоматически создают SQL-запросы
- Имеют встроенную валидацию

### **3. Git workflow:**
```
Локальные изменения → git add → git commit → git push
          ↓               ↓          ↓          ↓
       Работаете    Подготовка   Фиксация  Отправка
       с файлами    к коммиту    версии    на GitHub
```

### **4. SQLite vs PostgreSQL:**
- **Сейчас используем SQLite** - для разработки, один файл `db.sqlite3`
- **Позже перейдем на PostgreSQL** - для продакшена, через Docker

## **ПРОВЕРЬТЕ ЧТО У ВАС ЕСТЬ:**

### **Структура проекта сейчас:**
```
robo-well-control/
├── .venv/                    # Виртуальное окружение
├── .git/                    # Git репозиторий
├── config/                  # Настройки Django
├── core/                    # Наше приложение
│   ├── migrations/          # Файлы миграций
│   ├── models.py           # Модель Well
│   └── ...
├── db.sqlite3              # База данных
├── manage.py               # Управление Django
├── requirements.txt        # Библиотеки
└── .gitignore             # Игнорируемые файлы
```

### **Что в GitHub репозитории:**
- Все файлы проекта (кроме игнорируемых)
- История коммитов
- Готовая структура для продолжения разработки

## **СЛЕДУЮЩИЕ ШАГИ (когда будете готовы):**
1. Создание административного интерфейса для модели Well
2. Создание API endpoints для скважин
3. Добавление моделей для оборудования (насосы, двигатели)
4. Настройка Docker с PostgreSQL

**Ваш проект сейчас закоммичен и запушен на GitHub!** 🎉

# **ПАМЯТКА: RoboWell Control System (шаги 26-34)**

## **ЧТО МЫ СДЕЛАЛИ:**

### **АДМИНИСТРАТИВНЫЙ ИНТЕРФЕЙС:**

#### **26-27. Создали админку для модели Well:**
- **Файл:** `core/admin.py`
- **Русификация:** Без `gettext_lazy`, прямыми русскими строками
- **Фичи:**
  - Группировка полей (fieldsets)
  - Кастомные методы отображения
  - Только для чтения поля
  - Пагинация (20 на странице)

#### **28. Создали суперпользователя:**
```bash
python manage.py createsuperuser
```
- Логин: `admin`
- Пароль: ваш пароль
- **Ошибка и исправление:** Не был установлен `djangorestframework`

#### **29. Проверили админку:**
- URL: `http://127.0.0.1:8000/admin/`
- ✅ Русский интерфейс
- ✅ Раздел "Скважины"
- ✅ Форма добавления скважины

#### **30. Добавили тестовую скважину:**
- Название: "Скважина №1"
- Глубина: 2500 м
- Диаметр: 146 мм
- И другие параметры из ТЗ

### **REST API:**

#### **31. Создали сериализатор:**
- **Файл:** `core/serializers.py`
- **Класс:** `WellSerializer`
- **Что делает:** Преобразует модель ↔ JSON
- **Валидация:** Глубина, диаметр (проверка значений)
- **Кастомизация:** Добавление единиц измерения в JSON

#### **32. Создали ViewSet:**
- **Файл:** `core/views.py`
- **Класс:** `WellViewSet`
- **Фичи:**
  - Полный CRUD (GET, POST, PUT, PATCH, DELETE)
  - Фильтрация (`?min_depth=1000`)
  - Кастомные эндпоинты:
    - `/telemetry/` - телеметрия скважины
    - `/statistics/` - статистика по всем скважинам
  - Пагинация и сортировка

#### **33. Настроили URL:**
- **Файл:** `core/urls.py` - маршруты приложения
- **Файл:** `config/urls.py` - главные маршруты
- **Основной путь:** `/api/wells/`

#### **34. Протестировали API:**
- **URL тестирования:** `http://127.0.0.1:8000/api/wells/`
- **Исправленная ошибка:** Не хватало `from django.db import models`

## **ЧТО СЕЙЧАС РАБОТАЕТ:**

### **1. Админка Django:**
```
http://127.0.0.1:8000/admin/
→ Core
  → Скважины
    → Добавить скважину
    → Редактировать существующие
```

### **2. REST API:**
```
GET    /api/wells/                    # Все скважины
GET    /api/wells/1/                  # Конкретная скважина
GET    /api/wells/1/telemetry/        # Телеметрия
GET    /api/wells/statistics/         # Статистика
POST   /api/wells/                    # Добавить скважину
PUT    /api/wells/1/                  # Обновить скважину
DELETE /api/wells/1/                  # Удалить скважину
```

### **3. Данные:**
- SQLite база с таблицей `core_well`
- Тестовая скважина "Скважина №1"
- Все поля из ТЗ п.3.2

## **ТЕХНИЧЕСКИЕ ДЕТАЛИ:**

### **Структура проекта сейчас:**
```
robo-well-control/
├── core/
│   ├── admin.py          # Админка (русифицированная)
│   ├── models.py         # Модель Well
│   ├── serializers.py    # WellSerializer
│   ├── views.py          # WellViewSet
│   ├── urls.py           # Маршруты API
│   └── migrations/       # Миграции
├── config/
│   ├── settings.py       # Настройки (LANGUAGE_CODE='ru-ru')
│   └── urls.py           # Главные маршруты (+api/)
└── requirements.txt      # Библиотеки
```

### **Установленные библиотеки:**
- Django 4.2.11
- Django REST Framework 3.14.0
- SQLite (встроена в Python)

## **СООТВЕТСТВИЕ ТЗ:**

✅ **П.3.2** - Модель скважины с полями  
✅ **П.5** - Модульная структура  
✅ **П.7.1** - REST API для скважин  
✅ **П.12** - Документация (docstrings)  
🚧 **В процессе:** П.4.1 (остальные библиотеки)

## **СЛЕДУЮЩИЕ ШАГИ (когда будете готовы):**

1. **Добавить модели оборудования** (насосы, двигатели) - п.3.2
2. **Настроить Docker** с PostgreSQL - п.4.1
3. **Создать ML-модуль** - п.5.2
4. **Реализовать сбор телеметрии** - п.5.1

**Проект сейчас:** Рабочий backend с админкой и API для управления скважинами. Закоммичен и запущен на GitHub! 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 35-44)**

## **ЧТО МЫ СДЕЛАЛИ:**

### **РАБОТА С РЕАЛЬНЫМИ ДАННЫМИ НАСОСОВ ЭЦН:**

#### **35-38. Анализ структуры данных:**
- Изучили Excel файлы с характеристиками насосов
- Обнаружили формат: **1500+ насосов в одном файле**
- Поля: cod, Zavod, harka_stupen, material_stupen, Q, H, N, KPD, Left, Nominal, Right, minKPDROSNEFT

#### **39. Создание унифицированной модели `PumpCharacteristic`:**
- Объединили характеристики и основные параметры в одну модель
- **Автоматические расчеты при сохранении:**
  - `nominal_head` - напор при номинальной подаче
  - `stages_count` - извлечение из названия (ТД**1750**-200 → 1750 ступеней)
  - `optimal_flow_range` - где КПД ≥ minKPDROSNEFT
- **JSON поля** для хранения массивов данных (Q, H, N, KPD)

#### **40-41. Миграции базы данных:**
- Удалили модель `ESPump` (упрощение структуры)
- Создали новую таблицу `core_pumpcharacteristic`
- **Текущие модели:** Well, ElectricMotor, PumpCharacteristic

#### **42. Админка для новых моделей:**
- Русскоязычный интерфейс
- Группировка полей по смыслу
- Предпросмотр характеристик

#### **43-44. Система импорта Excel:**
```bash
# Структура команд
python manage.py import_pumps файл.xlsx          # Импорт одного файла
python manage.py import_pumps папка --folder     # Импорт всей папки
python manage.py import_pumps файл.xlsx --update # Обновить существующие
```

## **ТЕХНИЧЕСКИЕ ДЕТАЛИ:**

### **Структура модели `PumpCharacteristic`:**
```python
# Из Excel:
cod, zavod, harka_stupen, material_stupen
q_values, h_values, n_values, kpd_values (JSON массивы)
left_range, nominal_range, right_range, min_kpd_rosneft

# Автоматически вычисляемые:
nominal_head, stages_count, optimal_flow_range
housing_diameter=103.0 (стандарт), flow_part_material
```

### **Автоматические расчеты:**
1. **При сохранении модели:**
   - Напор при номинальной подаче
   - Количество ступеней из названия
   - Оптимальный диапазон работы

2. **Методы для инженерных расчетов:**
   - `calculate_at_point(q_value)` - параметры при заданной подаче
   - `get_qh_curve()` - данные для графика Q-H
   - `calculate_power_consumption()` - расчет мощности
   - `find_best_efficiency_point()` - точка максимального КПД

### **Архитектура импорта:**
```
Excel файл → pandas DataFrame → парсинг строк → 
→ преобразование данных → сохранение в PumpCharacteristic
```

## **ЧТО СЕЙЧАС РАБОТАЕТ:**

### **1. База данных:**
```
core_well              - Скважины (руссифицированные)
core_electricmotor     - Электродвигатели (по ГОСТ)
core_pumpcharacteristic - Насосы ЭЦН с характеристиками
```

### **2. Админка Django:**
```
http://127.0.0.1:8000/admin/
→ Core
  → Скважины
  → Электродвигатели  
  → Насосы ЭЦН (с характеристиками)
```

### **3. Импорт данных:**
- **Формат:** Excel с конкретной структурой
- **Объем:** 1500+ насосов в одном файле
- **Автоматизация:** Расчет всех технических параметров

### **4. REST API (ранее созданный):**
```
GET /api/wells/          - Список скважин
GET /api/wells/1/        - Конкретная скважина
... и другие эндпоинты
```

## **ВАЖНЫЕ ОСОБЕННОСТИ:**

### **Для работы с Excel:**
1. **Установлены библиотеки:** pandas, openpyxl
2. **Поддержка форматов:** .xlsx, .xls
3. **Обработка данных:** Запятые как десятичные разделители, пробелы как разделители значений

### **Автоматизация:**
- Извлечение числа ступеней из названия: `ТД1750-200` → 1750
- Расчет оптимального диапазона: где КПД ≥ стандарт Роснефти
- Интерполяция значений для любых точек подачи

### **Масштабируемость:**
- Одна модель для всех данных насосов
- JSON поля для хранения массивов
- Готово для 1500+ записей

## **СООТВЕТСТВИЕ ТЗ:**

✅ **П.3.2.2** - Характеристики насосов ЭЦН  
✅ **П.4.1** - Обработка данных (pandas)  
✅ **П.5.1** - Модуль сбора данных  
✅ **П.5.2** - Инженерные расчеты  
🚧 **В процессе:** ML модуль, веб-интерфейс

## **СЛЕДУЮЩИЕ ШАГИ (когда будете готовы):**

1. **Импорт реальных данных** (1500+ насосов)
2. **Создание API для насосов** (аналогично скважинам)
3. **Визуализация характеристик** (графики Q-H, Q-η)
4. **Подбор оборудования** (насос + двигатель для скважины)
5. **ML модуль** для прогнозирования и оптимизации

**Проект сейчас:** Готов к работе с реальными промышленными данными насосов ЭЦН. Имеет админку, API, систему импорта и автоматических расчетов. 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 45-47)**

## **РЕШЕНИЕ ПРОБЛЕМЫ С ОПТИМАЛЬНЫМ ДИАПАЗОНОМ**

### **Была проблема:**
- Оптимальный диапазон рассчитывался неправильно: `[0.0, 325.0]` или `[0.0, 0.0]`
- **Причина:** Алгоритм искал все точки где КПД ≥ 25% (min_kpd_rosneft)

### **Новая логика (правильная):**
**Оптимальный диапазон** = диапазон вокруг **точки максимального КПД**, где КПД не падает ниже **75% от максимального**.

### **Как работает новый алгоритм:**
1. **Находим максимальный КПД** из массива `kpd_values`
2. **Вычисляем порог:** 75% от максимального КПД
3. **Ищем границы:**
   - Левая граница: идем от точки max КПД влево, пока КПД ≥ порога
   - Правая граница: идем от точки max КПД вправо, пока КПД ≥ порога
4. **Если диапазон не найден** → используем рабочий диапазон `[left_range, right_range]`

### **Пример расчета:**
```
Данные насоса ТД1750-200:
Q:     [0, 25, 50, 75, 100, 125, 140, 175, 200, 225, 260, 275, 300, 325, 350]
КПД:   [0, 7.87, 15.05, 21.23, 26.26, 30.33, 32.41, 36.24, 37.89, 38.46, 37.57, 36.52, 33.21, 25.13, 0]

1. Max КПД = 38.46% (при Q=225)
2. 75% от max = 38.46 × 0.75 = 28.85%
3. Левая граница: Q=125 (КПД=30.33 ≥ 28.85)
4. Правая граница: Q=260 (КПД=37.57 ≥ 28.85)
5. Результат: оптимальный диапазон [125, 260]
```

## **ЧТО МЫ ИСПРАВИЛИ:**

### **45. Обновили модель `PumpCharacteristic`:**
- Добавили поля `max_efficiency` и `max_efficiency_flow`
- Исправили метод `save()` с новой логикой расчета
- Автоматический расчет при каждом сохранении

### **46. Добавили поля в базу и админку:**
```bash
# Создали миграции
python manage.py makemigrations core

# Применили миграции  
python manage.py migrate

# Обновили админку:
# - Добавили новые поля в list_display
# - Создали секцию "Оптимальные параметры"
```

### **47. Создали команды для исправления данных:**
```bash
# 1. Пересчет оптимальных диапазонов
python manage.py recalculate_pumps

# 2. Полный пересчет всех полей
python manage.py fix_pump_data
```

## **ТЕХНИЧЕСКИЕ ИЗМЕНЕНИЯ:**

### **Новые поля в модели:**
```python
max_efficiency = models.FloatField(...)       # Максимальный КПД, %
max_efficiency_flow = models.FloatField(...)  # Подача при max КПД, м³/сут
```

### **Логика в методе save():**
```python
def save(self, *args, **kwargs):
    # 1. Сначала вычисляем max КПД
    # 2. Потом оптимальный диапазон (75% от max)
    # 3. Затем номинальный напор
    # 4. И количество ступеней
    # Все автоматически при каждом сохранении
```

## **КАК ПРОВЕРИТЬ РАБОТУ:**

### **В админке (`http://127.0.0.1:8000/admin/`):**
1. Откройте "Насосы ЭЦН"
2. Проверьте колонки:
   - **Max КПД** - должно быть число (например, 38.46)
   - **Подача при max КПД** - должно быть число (например, 225)
   - **Оптимальный диапазон** - должно быть `[125, 260]`

### **В базе данных:**
```sql
-- В SQLite оболочке
SELECT harka_stupen, max_efficiency, max_efficiency_flow, optimal_flow_range 
FROM core_pumpcharacteristic;
```

## **ЕСЛИ ДАННЫЕ НЕ ЗАПОЛНЯЮТСЯ:**

### **Вариант 1: Команда исправления**
```bash
python manage.py fix_pump_data
```

### **Вариант 2: Переимпорт данных**
```bash
# Удалить старые данные
python manage.py shell
>>> from core.models import PumpCharacteristic
>>> PumpCharacteristic.objects.all().delete()

# Импортировать заново
python manage.py import_pumps ваш_файл.xlsx --update
```

### **Вариант 3: Ручное сохранение в админке**
1. Откройте насос в админке
2. Нажмите "Сохранить и продолжить редактирование"
3. Поля должны заполниться автоматически

## **ТЕКУЩИЙ СТАТУС:**

✅ **Все модели созданы:** Well, ElectricMotor, PumpCharacteristic  
✅ **Админка русифицирована**  
✅ **REST API для скважин работает**  
✅ **Импорт Excel данных работает**  
✅ **Автоматические расчеты работают**  
✅ **Оптимальные диапазоны рассчитываются правильно**  

## **СЛЕДУЮЩИЕ ЭТАПЫ:**

1. **Создание API для насосов и двигателей**
2. **Визуализация характеристик** (графики Q-H, Q-η)
3. **Система подбора оборудования** (насос + двигатель для скважины)
4. **ML модуль** для прогнозирования работы

**Проект готов к работе с реальными промышленными данными!** 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 48-50)**

## **СОЗДАНИЕ REST API ДЛЯ НАСОСОВ ЭЦН**

### **48. Создали сериализаторы для насосов:**

#### **PumpCharacteristicSerializer** (для детального просмотра):
- **Все поля** модели
- **Вычисляемые поля:**
  - `max_efficiency_display` - "38.46% при 225 м³/сут"
  - `optimal_range_display` - "125 - 260 м³/сут"
  - `characteristics_summary` - сводка характеристик
- **Валидация:** проверка массивов данных, согласованность длин

#### **PumpCharacteristicListSerializer** (для списка):
- **Только основные поля** (оптимизация)
- Форматированные отображения
- Флаг `has_full_characteristics`
- Количество точек в характеристиках

### **49. Создали ViewSet для насосов:**

#### **Основной функционал (CRUD):**
- `GET /api/pumps/` - список насосов
- `GET /api/pumps/{id}/` - детали насоса
- `POST/PUT/PATCH/DELETE` - управление

#### **Кастомные действия (actions):**
1. **`/characteristics/`** - полные данные для графиков
2. **`/calculate_point/`** - расчет параметров в точке
   ```bash
   /api/pumps/1/calculate_point/?flow=200&density=850
   ```
3. **`/find_suitable/`** - подбор насосов по параметрам
   ```bash
   /api/pumps/find_suitable/?required_flow=200&required_head=500
   ```
4. **`/statistics/`** - статистика по всем насосам

#### **Фильтрация и поиск:**
```bash
# По производителю
/api/pumps/?zavod=ESP

# По подаче
/api/pumps/?min_flow=100&max_flow=300

# По КПД
/api/pumps/?min_efficiency=30

# Поиск по названию
/api/pumps/?search=ТД1750

# Сортировка
/api/pumps/?ordering=-max_efficiency  # по КПД (убывание)
```

### **50. Настроили URL и окружение:**

#### **Добавили в `core/urls.py`:**
```python
router.register(r'pumps', PumpCharacteristicViewSet, basename='pump')
```

#### **Установили django-filter:**
```bash
pip install django-filter
```

#### **Добавили в `settings.py`:**
```python
INSTALLED_APPS = [
    # ...
    'django_filters',  # для фильтрации API
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,  # пагинация по 20 насосов
}
```

## **ЧТО СЕЙЧАС РАБОТАЕТ:**

### **API эндпоинты:**
```
✅ /api/wells/           - Скважины (созданы ранее)
✅ /api/pumps/           - Насосы ЭЦН (новые)
```

### **Для каждого насоса доступно:**
1. **Основная информация** - марка, производитель, параметры
2. **Характеристики** - массивы Q, H, N, КПД
3. **Оптимальный диапазон** - автоматически рассчитанный
4. **Максимальный КПД** - точка наилучшей эффективности

### **Фильтрация и поиск:**
- По производителю, материалу, количеству ступеней
- По диапазону подачи и напора
- По минимальному КПД
- Текстовый поиск по названию
- Сортировка по разным параметрам

## **ТЕХНИЧЕСКИЕ ОСОБЕННОСТИ:**

### **Оптимизация передачи данных:**
- **Для списка:** `PumpCharacteristicListSerializer` - только основные поля
- **Для деталей:** `PumpCharacteristicSerializer` - все поля + вычисляемые

### **Автоматические расчеты:**
```python
# В модели уже есть методы:
pump.calculate_at_point(200)        # параметры при Q=200
pump.calculate_power_consumption()  # расчет мощности
pump.get_qh_curve()                 # данные для графика
```

### **Валидация данных:**
- Проверка согласованности массивов Q, H, N, КПД
- Проверка что номинальная подача в рабочем диапазоне
- Проверка возрастания значений подачи

## **ПРОВЕРКА РАБОТЫ:**

### **1. Запустите сервер:**
```bash
python manage.py runserver
```

### **2. Проверьте эндпоинты в браузере:**
- `http://127.0.0.1:8000/api/pumps/` - список
- `http://127.0.0.1:8000/api/pumps/1/` - детали
- `http://127.0.0.1:8000/api/pumps/1/characteristics/` - графики

### **3. Проверьте фильтрацию:**
- `http://127.0.0.1:8000/api/pumps/?min_flow=100`
- `http://127.0.0.1:8000/api/pumps/?search=ТД1750`
- `http://127.0.0.1:8000/api/pumps/?ordering=-max_efficiency`

## **СООТВЕТСТВИЕ ТЗ:**

✅ **П.7.1** - REST API для оборудования  
✅ **П.5.2** - Инженерные расчеты  
✅ **П.4.1** - Обработка данных  
✅ **П.3.2.2** - Хранение характеристик  

## **СЛЕДУЮЩИЕ ШАГИ:**

1. **API для электродвигателей** (аналогично насосам)
2. **Визуализация графиков** в веб-интерфейсе
3. **Система подбора** насос+двигатель для скважины
4. **Интеграция ML-моделей** для прогнозирования

**Проект имеет полноценный REST API для работы с насосами ЭЦН!** 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 51-54)**

## **ПЕРЕХОД НА РЕАЛЬНЫЕ ДАННЫЕ ЭЛЕКТРОДВИГАТЕЛЕЙ**

### **Проблема:**
Изначальная модель `ElectricMotor` не соответствовала реальной структуре Excel файлов с данными двигателей.

### **Решение:**
Полностью переработали модель под реальную структуру данных.

## **51. АНАЛИЗ СТРУКТУРЫ EXCEL ФАЙЛА:**

### **Столбцы в вашем Excel файле:**
```
ID, Model, Power_nom, U_nom, I_nom, Turning, TurningMoment,
R_ColdWinding, BoringMoment, U_accel, I_Idling, P_HeatedWaste,
U_InsulWinding, U_MinInsulWinding, Time_RunDown, VibrLevel,
U_Idling, R_Insul, P_h_h, I_k_z, U_k_z, dR_ColdWinding,
Manufactured, P_k_z, S_load, Powerfactor_load, Efficiency_load
```

### **Игнорируемые столбцы (по вашим указаниям):**
```
I_h_h, U_k_z_0, P_k_z_0, I_load, M_Power_load
```

## **52. СОЗДАНИЕ НОВОЙ МОДЕЛИ ELECTRICMOTOR:**

### **Ключевые поля модели:**
```python
# Идентификация
motor_id, model, manufacturer

# Номинальные параметры  
nominal_power, nominal_voltage, nominal_current

# Механические характеристики
rotation_speed, torque, shaft_torque, vibration_level

# Электрические характеристики
cold_winding_resistance, acceleration_voltage, idle_current

# Испытания и измерения
insulation_test_voltage, insulation_resistance, rundown_time

# Параметры КЗ
short_circuit_current, short_circuit_voltage, short_circuit_power

# Рабочие параметры
slip, power_factor, efficiency

# Метаданные
source_file, created_at, updated_at
```

### **Расчетные методы модели:**
1. `calculate_rated_torque_nm()` - номинальный момент (Н·м)
2. `calculate_starting_current_ratio()` - кратность пускового тока
3. `get_vibration_status()` - оценка вибрации по ГОСТ
4. `calculate_efficiency_class()` - класс энергоэффективности (IE1/IE2/IE3)
5. `calculate_power_consumption()` - расчет потребления

## **53. ПРОБЛЕМЫ И РЕШЕНИЯ ПРИ МИГРАЦИИ:**

### **Возникшие ошибки:**
1. **Ошибка 1:** `'ordering' refers to nonexistent field 'manufacturer'`
   - **Решение:** Убрали `manufacturer` из ordering в классе Meta

2. **Ошибка 2:** Невозможно добавить non-nullable поля без default
   - **Решение:** Добавили `default` значения для всех полей

3. **Ошибка 3:** Несоответствие названий полей
   - **Решение:** Полное обновление модели под Excel структуру

### **Команды для исправления:**
```bash
# Создание миграций
python manage.py makemigrations core

# Применение миграций  
python manage.py migrate

# Очистка старых данных
python manage.py shell
>>> from core.models import ElectricMotor
>>> ElectricMotor.objects.all().delete()
```

## **54. СИСТЕМА ИМПОРТА ИЗ EXCEL:**

### **Команда импорта:**
```bash
# Базовый импорт
python manage.py import_motors файл.xlsx

# Импорт с обновлением существующих
python manage.py import_motors файл.xlsx --update

# Импорт с указанием листа
python manage.py import_motors файл.xlsx --sheet "Лист1"
```

### **Логика работы парсера:**
1. **Загрузка Excel:** pandas.read_excel()
2. **Проверка обязательных полей:** ID, Model, Power_nom, U_nom, I_nom
3. **Преобразование данных:** Замена запятых, обработка NaN
4. **Сохранение:** Создание или обновление записей в базе

### **Формат преобразования данных:**
```python
# Строки → числа с заменой запятых
"123,45" → 123.45

# Пустые значения → 0.0
NaN → 0.0

# Строки → обрезанные строки
"  ЭД-16  " → "ЭД-16"
```

## **ЧТО СЕЙЧАС РАБОТАЕТ:**

### **✅ Модели данных:**
1. **Well** - скважины (геологические параметры)
2. **PumpCharacteristic** - насосы ЭЦН с характеристиками
3. **ElectricMotor** - электродвигатели (реальная структура Excel)

### **✅ Административные интерфейсы:**
- Русскоязычные формы
- Группировка полей по смыслу
- Валидация данных
- Расчетные поля

### **✅ Системы импорта:**
- Насосы из Excel (1500+ записей)
- Электродвигатели из Excel (реальная структура)
- Автоматические расчеты при импорте

### **✅ REST API:**
- Скважины (WellViewSet)
- Насосы (PumpCharacteristicViewSet)
- *В процессе:* Электродвигатели

## **ТЕХНИЧЕСКИЕ ОСОБЕННОСТИ:**

### **Архитектура импорта:**
```
Excel файл → pandas DataFrame → парсинг строк → 
→ преобразование типов → сохранение в Django модели
```

### **Обработка ошибок:**
- Пропуск строк с отсутствующими обязательными полями
- Логирование успешных и неудачных операций
- Транзакционность (atomic) для целостности данных

### **Расчетные возможности:**
- **Для насосов:** Q-H характеристики, оптимальные диапазоны, КПД
- **Для двигателей:** классы энергоэффективности, оценка вибрации, потребление

## **ПРОВЕРКА РАБОТОСПОСОБНОСТИ:**

### **1. Тестовые данные:**
```bash
# Создание тестовых файлов
python create_test_motors.py      # 3 простых двигателя
python create_realistic_motors.py # 10 реалистичных двигателей
```

### **2. Импорт и проверка:**
```bash
# Импорт
python manage.py import_motors realistic_motors.xlsx --update

# Проверка в базе
python manage.py shell
>>> from core.models import ElectricMotor
>>> print(f"Двигателей: {ElectricMotor.objects.count()}")
>>> motor = ElectricMotor.objects.first()
>>> print(f"Первый: {motor.model}, {motor.nominal_power} кВт")
```

### **3. Проверка в админке:**
```
http://127.0.0.1:8000/admin/core/electricmotor/
→ Все поля заполнены
→ Расчетные методы работают
→ Данные соответствуют Excel
```

## **СЛЕДУЮЩИЕ ЭТАПЫ:**

### **Ближайшие шаги:**
1. **API для электродвигателей** - аналогично насосам
2. **Визуализация характеристик** - графики Q-H, вибрации, КПД
3. **Связывание оборудования** - насос + двигатель + скважина

### **Дальнейшее развитие:**
4. **Система подбора** - автоматический подбор оборудования
5. **ML модуль** - прогнозирование параметров и отказов
6. **Веб-интерфейс** - Dash/Plotly для визуализации

**Проект теперь работает с реальными промышленными данными насосов и электродвигателей!** 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 55-58)**

## **СОЗДАНИЕ REST API ДЛЯ ЭЛЕКТРОДВИГАТЕЛЕЙ И СВЯЗЕЙ**

### **55. ПОЛНЫЙ REST API ДЛЯ ЭЛЕКТРОДВИГАТЕЛЕЙ**

#### **Сериализаторы (serializers_motors.py):**

**ElectricMotorSerializer** (полный):
- Все поля модели + вычисляемые:
  - `rated_torque_display` - момент в Н·м
  - `starting_current_ratio_display` - кратность пускового тока
  - `vibration_status_display` - статус вибрации с цветом
  - `efficiency_class_display` - класс IE1/IE2/IE3
  - `power_consumption_summary` - потребление энергии
  - `technical_summary` - сводка характеристик

**ElectricMotorListSerializer** (упрощенный для списка):
- Основные поля: модель, мощность, напряжение, ток, КПД
- `power_consumption_daily` - суточное потребление
- `condition_summary` - сводка состояния (вибрация, изоляция, КПД)

#### **ViewSet (views_motors.py):**

**Основные эндпоинты:**
```
GET    /api/motors/              - список двигателей
GET    /api/motors/{id}/         - детали двигателя
POST   /api/motors/              - создать двигатель
PUT    /api/motors/{id}/         - обновить
DELETE /api/motors/{id}/         - удалить
```

**Специальные эндпоинты:**
```
GET    /api/motors/{id}/technical_analysis/     - тех. анализ
GET    /api/motors/{id}/compare_with_standard/  - сравнение с ГОСТ
GET    /api/motors/find_for_pump/                - подбор для насоса
GET    /api/motors/efficiency_statistics/       - статистика КПД
```

**Фильтрация и поиск:**
```bash
# По мощности
/api/motors/?min_power=30&max_power=50

# По КПД
/api/motors/?min_efficiency=85

# По напряжению
/api/motors/?voltage=530

# По вибрации
/api/motors/?max_vibration=4.5

# Поиск по модели
/api/motors/?search=ЭДСТ
```

### **56-57. ИСПРАВЛЕНИЕ ОШИБОК**

**Проблема 1:** `_generate_recommendations` не был определен
- **Решение:** Добавлен метод с рекомендациями по вибрации, изоляции, КПД, нагреву

**Проблема 2:** `get_vibraion_status` (опечатка) vs `get_vibration_status`
- **Решение:** Исправлено название метода в модели

**Метод get_vibration_status в модели:**
```python
def get_vibration_status(self):
    if level <= 2.8:    # Отличное
    elif level <= 4.5:  # Хорошее  
    elif level <= 7.1:  # Удовлетворительное
    else:               # Критическое
```

### **58. СВЯЗЫВАНИЕ НАСОСОВ И ДВИГАТЕЛЕЙ**

#### **Добавление поля в модель PumpCharacteristic:**
```python
recommended_motor = models.ForeignKey(
    'ElectricMotor',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='suitable_pumps',
    verbose_name="Рекомендуемый двигатель"
)
```

#### **Новый эндпоинт для подбора двигателя к насосу:**
```
GET /api/pumps/{id}/find_matching_motor/
    ?service_factor=1.15
    &min_efficiency=80
```

**Что возвращает:**
- Данные насоса (мощность на валу, требуемая мощность)
- Список подходящих двигателей с:
  - `power_match_percentage` - насколько мощность соответствует
  - `actual_service_factor` - реальный коэффициент запаса
  - статус вибрации, класс КПД

#### **Команда для автоматического подбора:**
```bash
# Базовый запуск
python manage.py match_pumps_motors

# С другим коэффициентом запаса
python manage.py match_pumps_motors --service-factor 1.2

# Принудительное обновление всех
python manage.py match_pumps_motors --update-all
```

#### **Обновленный сериализатор насосов:**
```python
# В PumpCharacteristicSerializer добавлено:
recommended_motor_info = {
    'id': motor.id,
    'model': motor.model,
    'manufacturer': motor.manufacturer,
    'nominal_power': motor.nominal_power,
    'nominal_voltage': motor.nominal_voltage,
    'efficiency': motor.efficiency
}
```

## **ТЕКУЩАЯ СТРУКТУРА API:**

```
/api/wells/              # Скважины
  ├── /{id}/telemetry/   # Телеметрия
  └── /{id}/predictions/ # Прогнозы

/api/pumps/              # Насосы ЭЦН
  ├── /{id}/characteristics/    # Характеристики Q-H
  ├── /{id}/calculate_point/    # Расчет точки
  ├── /{id}/find_matching_motor/ # Подбор двигателя
  └── /find_suitable/           # Подбор по параметрам

/api/motors/             # Электродвигатели
  ├── /{id}/technical_analysis/    # Технический анализ
  ├── /{id}/compare_with_standard/ # Сравнение с ГОСТ
  ├── /find_for_pump/              # Подбор для насоса
  └── /efficiency_statistics/      # Статистика КПД
```

## **РАСЧЕТНЫЕ МЕТОДЫ В МОДЕЛЯХ:**

### **PumpCharacteristic:**
- `calculate_at_point(q)` - параметры при заданной подаче
- `calculate_power_consumption()` - расчет мощности
- `get_qh_curve()` - данные для графика Q-H
- `find_best_efficiency_point()` - точка max КПД

### **ElectricMotor:**
- `calculate_rated_torque_nm()` - момент в Н·м
- `calculate_starting_current_ratio()` - кратность пускового тока
- `get_vibration_status()` - оценка вибрации
- `calculate_efficiency_class()` - класс IE
- `calculate_power_consumption()` - потребление энергии

## **ПРОВЕРКА РАБОТЫ:**

### **1. Запуск сервера:**
```bash
python manage.py runserver
```

### **2. Проверка API двигателей:**
- `http://127.0.0.1:8000/api/motors/` - список
- `http://127.0.0.1:8000/api/motors/1/` - детали
- `http://127.0.0.1:8000/api/motors/1/technical_analysis/` - анализ
- `http://127.0.0.1:8000/api/motors/find_for_pump/?pump_power=30` - подбор

### **3. Проверка связей:**
```bash
# Подобрать двигатели для насоса №1
http://127.0.0.1:8000/api/pumps/1/find_matching_motor/

# Запустить автоматический подбор
python manage.py match_pumps_motors --update-all
```

## **СООТВЕТСТВИЕ ТЗ:**

✅ **П.3.2.1** - Электродвигатели (полная модель)  
✅ **П.3.2.2** - Насосы ЭЦН (с характеристиками)  
✅ **П.3.2.3** - Скважины  
✅ **П.7.1** - REST API для всех сущностей  
✅ **П.5.2** - Инженерные расчеты (КПД, мощность, вибрация)  
🚧 **В процессе:** ML модуль, веб-интерфейс

## **СЛЕДУЮЩИЕ ШАГИ:**

1. **Визуализация характеристик** (Plotly/Dash)
2. **ML модуль** для прогнозирования
3. **Веб-интерфейс** для управления
4. **Интеграция с промышленными протоколами** (Modbus, OPC UA)

**Проект имеет полноценный REST API для всех трех основных сущностей с расчетными методами и связями между ними!** 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 55-58)**

## **СОЗДАНИЕ REST API ДЛЯ ЭЛЕКТРОДВИГАТЕЛЕЙ И СВЯЗЕЙ**

### **55. ПОЛНЫЙ REST API ДЛЯ ЭЛЕКТРОДВИГАТЕЛЕЙ**

#### **Сериализаторы (serializers_motors.py):**

**ElectricMotorSerializer** (полный):
- Все поля модели + вычисляемые:
  - `rated_torque_display` - момент в Н·м
  - `starting_current_ratio_display` - кратность пускового тока
  - `vibration_status_display` - статус вибрации с цветом
  - `efficiency_class_display` - класс IE1/IE2/IE3
  - `power_consumption_summary` - потребление энергии
  - `technical_summary` - сводка характеристик

**ElectricMotorListSerializer** (упрощенный для списка):
- Основные поля: модель, мощность, напряжение, ток, КПД
- `power_consumption_daily` - суточное потребление
- `condition_summary` - сводка состояния (вибрация, изоляция, КПД)

#### **ViewSet (views_motors.py):**

**Основные эндпоинты:**
```
GET    /api/motors/              - список двигателей
GET    /api/motors/{id}/         - детали двигателя
POST   /api/motors/              - создать двигатель
PUT    /api/motors/{id}/         - обновить
DELETE /api/motors/{id}/         - удалить
```

**Специальные эндпоинты:**
```
GET    /api/motors/{id}/technical_analysis/     - тех. анализ
GET    /api/motors/{id}/compare_with_standard/  - сравнение с ГОСТ
GET    /api/motors/find_for_pump/                - подбор для насоса
GET    /api/motors/efficiency_statistics/       - статистика КПД
```

**Фильтрация и поиск:**
```bash
# По мощности
/api/motors/?min_power=30&max_power=50

# По КПД
/api/motors/?min_efficiency=85

# По напряжению
/api/motors/?voltage=530

# По вибрации
/api/motors/?max_vibration=4.5

# Поиск по модели
/api/motors/?search=ЭДСТ
```

### **56-57. ИСПРАВЛЕНИЕ ОШИБОК**

**Проблема 1:** `_generate_recommendations` не был определен
- **Решение:** Добавлен метод с рекомендациями по вибрации, изоляции, КПД, нагреву

**Проблема 2:** `get_vibraion_status` (опечатка) vs `get_vibration_status`
- **Решение:** Исправлено название метода в модели

**Метод get_vibration_status в модели:**
```python
def get_vibration_status(self):
    if level <= 2.8:    # Отличное
    elif level <= 4.5:  # Хорошее  
    elif level <= 7.1:  # Удовлетворительное
    else:               # Критическое
```

### **58. СВЯЗЫВАНИЕ НАСОСОВ И ДВИГАТЕЛЕЙ**

#### **Добавление поля в модель PumpCharacteristic:**
```python
recommended_motor = models.ForeignKey(
    'ElectricMotor',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='suitable_pumps',
    verbose_name="Рекомендуемый двигатель"
)
```

#### **Новый эндпоинт для подбора двигателя к насосу:**
```
GET /api/pumps/{id}/find_matching_motor/
    ?service_factor=1.15
    &min_efficiency=80
```

**Что возвращает:**
- Данные насоса (мощность на валу, требуемая мощность)
- Список подходящих двигателей с:
  - `power_match_percentage` - насколько мощность соответствует
  - `actual_service_factor` - реальный коэффициент запаса
  - статус вибрации, класс КПД

#### **Команда для автоматического подбора:**
```bash
# Базовый запуск
python manage.py match_pumps_motors

# С другим коэффициентом запаса
python manage.py match_pumps_motors --service-factor 1.2

# Принудительное обновление всех
python manage.py match_pumps_motors --update-all
```

#### **Обновленный сериализатор насосов:**
```python
# В PumpCharacteristicSerializer добавлено:
recommended_motor_info = {
    'id': motor.id,
    'model': motor.model,
    'manufacturer': motor.manufacturer,
    'nominal_power': motor.nominal_power,
    'nominal_voltage': motor.nominal_voltage,
    'efficiency': motor.efficiency
}
```

## **ТЕКУЩАЯ СТРУКТУРА API:**

```
/api/wells/              # Скважины
  ├── /{id}/telemetry/   # Телеметрия
  └── /{id}/predictions/ # Прогнозы

/api/pumps/              # Насосы ЭЦН
  ├── /{id}/characteristics/    # Характеристики Q-H
  ├── /{id}/calculate_point/    # Расчет точки
  ├── /{id}/find_matching_motor/ # Подбор двигателя
  └── /find_suitable/           # Подбор по параметрам

/api/motors/             # Электродвигатели
  ├── /{id}/technical_analysis/    # Технический анализ
  ├── /{id}/compare_with_standard/ # Сравнение с ГОСТ
  ├── /find_for_pump/              # Подбор для насоса
  └── /efficiency_statistics/      # Статистика КПД
```

## **РАСЧЕТНЫЕ МЕТОДЫ В МОДЕЛЯХ:**

### **PumpCharacteristic:**
- `calculate_at_point(q)` - параметры при заданной подаче
- `calculate_power_consumption()` - расчет мощности
- `get_qh_curve()` - данные для графика Q-H
- `find_best_efficiency_point()` - точка max КПД

### **ElectricMotor:**
- `calculate_rated_torque_nm()` - момент в Н·м
- `calculate_starting_current_ratio()` - кратность пускового тока
- `get_vibration_status()` - оценка вибрации
- `calculate_efficiency_class()` - класс IE
- `calculate_power_consumption()` - потребление энергии

## **ПРОВЕРКА РАБОТЫ:**

### **1. Запуск сервера:**
```bash
python manage.py runserver
```

### **2. Проверка API двигателей:**
- `http://127.0.0.1:8000/api/motors/` - список
- `http://127.0.0.1:8000/api/motors/1/` - детали
- `http://127.0.0.1:8000/api/motors/1/technical_analysis/` - анализ
- `http://127.0.0.1:8000/api/motors/find_for_pump/?pump_power=30` - подбор

### **3. Проверка связей:**
```bash
# Подобрать двигатели для насоса №1
http://127.0.0.1:8000/api/pumps/1/find_matching_motor/

# Запустить автоматический подбор
python manage.py match_pumps_motors --update-all
```

## **СООТВЕТСТВИЕ ТЗ:**

✅ **П.3.2.1** - Электродвигатели (полная модель)  
✅ **П.3.2.2** - Насосы ЭЦН (с характеристиками)  
✅ **П.3.2.3** - Скважины  
✅ **П.7.1** - REST API для всех сущностей  
✅ **П.5.2** - Инженерные расчеты (КПД, мощность, вибрация)  
🚧 **В процессе:** ML модуль, веб-интерфейс

## **СЛЕДУЮЩИЕ ШАГИ:**

1. **Визуализация характеристик** (Plotly/Dash)
2. **ML модуль** для прогнозирования
3. **Веб-интерфейс** для управления
4. **Интеграция с промышленными протоколами** (Modbus, OPC UA)

**Проект имеет полноценный REST API для всех трех основных сущностей с расчетными методами и связями между ними!** 🚀

# **ПАМЯТКА: RoboWell Control System (шаги 69-80)**

## **ТЕКУЩАЯ АРХИТЕКТУРА ПРОЕКТА**

### **1. МОДЕЛИ ДАННЫХ (core/models.py)**

```python
# Скважина
Well - основная информация, external_id для связи с внешними системами

# Телеметрия  
TelemetryData - все параметры работы скважины + raw_data (полный JSON)

# Оборудование
PumpCharacteristic - характеристики насосов с Q-H кривыми
ElectricMotor - параметры электродвигателей

# Уведомления
Alert - превышение порогов (давление, температура, вибрация)

# Аудит
CommandLog - логи всех отправленных команд
```

### **2. ВНЕШНИЕ ИНТЕГРАЦИИ**

#### **Получение телеметрии (TelemetryAPIClient):**
- **Запрос:** `GET /public-api/wells/{well_id}/telemetry`
- **Парсинг:** гибкий, поддерживает разные форматы
- **Хранение:** все сырые данные в `raw_data`
- **Проверка порогов:** автоматически создает уведомления

#### **Отправка команд (ControlService):**
- **Запрос:** `POST /commands` с JSON телом
- **Валидация:** частота (30-60 Гц), ток (<200 А)
- **Логирование:** все команды сохраняются в `CommandLog`
- **Аудит:** кто, когда, какую команду отправил

### **3. API ЭНДПОИНТЫ**

```
/api/wells/           - управление скважинами
/api/pumps/           - насосы с характеристиками
/api/motors/          - электродвигатели
/api/telemetry/       - данные телеметрии
/api/alerts/          - уведомления о превышениях
/api/command-logs/    - аудит команд
/api/control/         - отправка команд
```

### **4. ВЕБ-ИНТЕРФЕЙС**

```
/                   - дашборд со статистикой
/wells/             - список скважин
/wells/{id}/        - детали скважины
/wells/{id}/telemetry/ - таблица телеметрии
/wells/{id}/dashboard/ - графики (Plotly)
/pumps/             - список насосов
/motors/            - список двигателей
/alerts/            - уведомления
```

### **5. АВТОМАТИЗАЦИЯ**

```bash
# Получение телеметрии
python manage.py fetch_telemetry --well-id 1
python manage.py fetch_telemetry  # для всех

# Автоматическая регулировка
python manage.py auto_adjust --well-id 1
python manage.py auto_adjust  # для всех

# Проверка уведомлений
python manage.py check_alerts
```

### **6. БЕЗОПАСНОСТЬ**

- **Валидация** всех входящих команд
- **Логирование** всех действий
- **Проверка** диапазонов параметров
- **Аудит** кто и когда отправлял команды

### **7. РАСШИРЯЕМОСТЬ**

- **raw_data** в телеметрии - сохраняются все данные на будущее
- **external_id** - для связи с внешними системами
- **JSON поля** - гибкое хранение характеристик
- **Пороги** - легко менять в AlertService

### **8. ЧТО ДАЛЬШЕ**

1. Celery для автоматического опроса телеметрии
2. ML модели для прогнозирования
3. Автоматический вывод на режим
4. Интеграция с SCADA системами

# **ПАМЯТКА: RoboWell Control System (шаги 78-84)**

## **СИСТЕМА УПРАВЛЕНИЯ (CONTROL SERVICE)**

### **1. Модели для управления**

#### **CommandLog (core/models.py)**
```python
- well          - скважина
- command_type  - тип команды (start/stop/emergency_stop/frequency_adjust)
- parameters    - параметры команды (JSON)
- status        - статус (sent/success/error)
- response      - ответ внешней системы
- created_at    - время создания
```

### **2. Сервис управления (core/services/control_service.py)**

```python
# Основные методы
send_command()      - отправка любой команды
set_frequency()     - установка частоты
emergency_stop()    - аварийная остановка
start()             - пуск
stop()              - останов
calculate_optimal_frequency() - расчет оптимальной частоты
```

### **3. API эндпоинты**

```
POST   /api/control/adjust_frequency/   - отправка команды
GET    /api/control/optimal/            - расчет оптимальной частоты
```

### **4. Веб-интерфейс**

#### **Модальное окно управления (well_detail.html)**
- Ползунок частоты (30-60 Гц)
- Ползунок времени разгона (10-120 с)
- Кнопки: Пуск, Стоп, Аварийная остановка
- Кнопка: Установить частоту
- Кнопка: Рассчитать оптимальную частоту

#### **История команд (command_logs.html)**
- Таблица всех команд
- Статусы (цветные бейджи)
- Время выполнения
- Параметры команды

### **5. Тестовый режим**

Временно в `send_command`:
```python
return {
    'status': 'success',
    'message': 'Команда принята (тестовый режим)',
    'command': command
}
```

### **6. Проверка работы**

```bash
# 1. Запустить сервер
python manage.py runserver

# 2. Открыть скважину
http://127.0.0.1:8000/wells/1/

# 3. Нажать "Управление" → тестировать кнопки

# 4. Проверить логи
http://127.0.0.1:8000/commands/
```

### **7. Следующие шаги**

1. Подключение к реальному API управления
2. ML алгоритмы для оптимальной частоты
3. Автоматический режим (без участия оператора)
4. Безопасность (подтверждение критических команд)