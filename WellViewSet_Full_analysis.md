# 📚 Полный конспект WellViewSet для начинающих

## 🎯 Общая концепция
**WellViewSet** — это класс на Django REST Framework (DRF), который реализует **полный REST API** для модели "Скважина" (Well). Он обрабатывает все стандартные операции (CRUD) и добавляет дополнительные функции.

## 📁 Импорты (начало файла)
```python
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Well
from .serializers import WellSerializer
```
- **viewsets** — содержит базовые классы для ViewSet'ов
- **permissions** — классы для контроля доступа
- **Response** — для возврата структурированных ответов
- **action** — декоратор для создания дополнительных эндпоинтов
- **get_object_or_404** — удобная функция для получения объекта или ошибки 404
- **Well, WellSerializer** — наша модель и сериализатор

## 🏗️ Создание класса WellViewSet

### 1️⃣ **Наследование от ModelViewSet**
```python
class WellViewSet(viewsets.ModelViewSet):
```
**ModelViewSet** — это "волшебный" класс DRF, который автоматически предоставляет:
- `list()` — GET /api/wells/ (список)
- `create()` — POST /api/wells/ (создание)
- `retrieve()` — GET /api/wells/{id}/ (получение одного)
- `update()` — PUT /api/wells/{id}/ (полное обновление)
- `partial_update()` — PATCH /api/wells/{id}/ (частичное обновление)
- `destroy()` — DELETE /api/wells/{id}/ (удаление)

### 2️⃣ **Базовый QuerySet**
```python
queryset = Well.objects.all()
```
Определяет **базовый набор данных** — все объекты модели Well. DRF будет использовать его как точку отсчета для всех операций.

### 3️⃣ **Сериализатор**
```python
serializer_class = WellSerializer
```
Указывает, какой класс преобразует:
- **Объекты Python → JSON** (при отправке клиенту)
- **JSON → Объекты Python** (при получении от клиента)
Сериализатор также **валидирует данные** перед сохранением.

### 4️⃣ **Права доступа**
```python
permission_classes = [permissions.IsAuthenticatedOrReadOnly]
```
- **Анонимные пользователи**: только чтение (GET, HEAD, OPTIONS)
- **Авторизованные пользователи**: все операции (POST, PUT, PATCH, DELETE)

## 🔍 Метод `get_queryset()` — "умная" фильтрация

### Цель метода
Возвращает **динамический QuerySet** в зависимости от параметров запроса.

### Логика работы
```python
def get_queryset(self):
    # 1. Берём базовый QuerySet (все скважины)
    queryset = super().get_queryset()
    
    # 2. Получаем параметры из URL
    min_depth = self.request.query_params.get('min_depth')
    max_depth = self.request.query_params.get('max_depth')
    
    # 3. Фильтруем по минимальной глубине
    if min_depth:
        queryset = queryset.filter(depth__gte=float(min_depth))
    
    # 4. Фильтруем по максимальной глубине  
    if max_depth:
        queryset = queryset.filter(depth__lte=float(max_depth))
    
    # 5. Сортируем результат по имени
    return queryset.order_by('name')
```

### 🔑 Ключевые понятия
- **`query_params`** — словарь параметров из URL (после `?`)
- **`depth__gte`** — lookup "больше или равно" (≥)
- **`depth__lte`** — lookup "меньше или равно" (≤)
- **Фильтры комбинируются** через AND (логическое "И")

### 📝 Примеры запросов
- `/api/wells/` — все скважины
- `/api/wells/?min_depth=1000` — скважины глубже 1000м
- `/api/wells/?min_depth=1000&max_depth=2000` — скважины от 1000м до 2000м

## 🎛️ Кастомные действия (Custom Actions)

### 1️⃣ **Телеметрия скважины** (для одного объекта)
```python
@action(detail=True, methods=['get'])
def telemetry(self, request, pk=None):
    well = self.get_object()  # Получаем скважину по ID
    telemetry_data = { ... }  # Тестовые данные
    return Response(telemetry_data)
```

#### 🌐 URL: `/api/wells/{id}/telemetry/`
- **`detail=True`** — действие для конкретного объекта (требует ID)
- **`methods=['get']`** — только GET запросы
- **`self.get_object()`** — получает объект по `pk` (primary key)

#### 📊 Возвращаемые данные (заглушка):
```json
{
    "well_id": 5,
    "well_name": "Скважина-1",
    "status": "active",
    "current_frequency": 50.0,
    "current_pressure": 15.5,
    "current_temperature": 85.0,
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2️⃣ **Статистика по всем скважинам** (для коллекции)
```python
@action(detail=False, methods=['get'])
def statistics(self, request):
    wells = self.get_queryset()  # Уже отфильтрованный QuerySet!
    stats = { ... }  # Рассчитываем статистику
    return Response(stats)
```

#### 🌐 URL: `/api/wells/statistics/`
- **`detail=False`** — действие для всей коллекции (без ID)
- Использует `get_queryset()` → учитывает фильтры из запроса

## 📊 Агрегатные функции Django (статистика)

### Что такое агрегация?
Вычисление **общих показателей** по набору записей:

```python
# Подсчёт количества
wells.count()  # → 5 (выполняет SELECT COUNT(*))

# Агрегация нескольких показателей сразу
result = wells.aggregate(
    models.Avg('depth'),    # Средняя глубина
    models.Max('depth'),    # Максимальная глубина  
    models.Min('depth'),    # Минимальная глубина
    models.Sum('formation_debit')  # Суммарный дебит
)

# Результат — словарь:
{
    'depth__avg': 1524.75,
    'depth__max': 3000.0,
    'depth__min': 500.0,
    'formation_debit__sum': 12500.0
}

# Извлечение значения по ключу:
avg_depth = result['depth__avg']  # 1524.75
```

### 📝 Полный код статистики:
```python
stats = {
    'total_wells': wells.count(),
    'avg_depth': wells.aggregate(models.Avg('depth'))['depth__avg'] if wells.exists() else 0,
    'max_depth': wells.aggregate(models.Max('depth'))['depth__max'] if wells.exists() else 0,
    'min_depth': wells.aggregate(models.Min('depth'))['depth__min'] if wells.exists() else 0,
    'total_debit': wells.aggregate(models.Sum('formation_debit'))['formation_debit__sum'] if wells.exists() else 0
}
```

#### 🛡️ Защита от пустого QuerySet:
`if wells.exists() else 0` — если скважин нет, возвращаем 0 вместо ошибки

## ⚡ Хуки (Hooks) — кастомизация операций

### 1️⃣ **При создании скважины** (`perform_create`)
```python
def perform_create(self, serializer):
    serializer.save()  # Сохраняем объект в БД
    # TODO: Логирование, уведомления и т.д.
```

#### 🎯 Когда вызывается:
- После валидации данных в `WellSerializer`
- Перед сохранением в базу
- Для запроса `POST /api/wells/`

#### 💡 Что можно добавить:
```python
def perform_create(self, serializer):
    # Привязка к пользователю
    well = serializer.save(created_by=self.request.user)
    
    # Логирование
    logger.info(f"Создана скважина {well.name}")
    
    # Создание связанных объектов
    Telemetry.objects.create(well=well, status='new')
    
    # Отправка уведомления
    send_email_notification(well)
```

### 2️⃣ **При удалении скважины** (`perform_destroy`)
```python
def perform_destroy(self, instance):
    # TODO: Проверка зависимостей, логирование
    instance.delete()  # Удаляем объект из БД
```

#### 🎯 Когда вызывается:
- После получения объекта (по ID)
- Перед фактическим удалением из базы
- Для запроса `DELETE /api/wells/{id}/`

#### ⚠️ Важные проверки перед удалением:
```python
def perform_destroy(self, instance):
    # 1. Проверка зависимостей
    if instance.measurements.exists():
        return Response(
            {"error": "Нельзя удалить: есть связанные измерения"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 2. Логирование
    logger.warning(f"Удаление скважины {instance.id}")
    
    # 3. Архивирование
    archive_well_data(instance)
    
    # 4. Удаление
    instance.delete()
```

## 🗺️ Полная карта API эндпоинтов

| Метод | URL | Действие | Доступ |
|-------|-----|----------|--------|
| GET | `/api/wells/` | Список всех скважин | Все |
| POST | `/api/wells/` | Создание скважины | Только авторизованные |
| GET | `/api/wells/{id}/` | Детали скважины | Все |
| PUT | `/api/wells/{id}/` | Полное обновление | Только авторизованные |
| PATCH | `/api/wells/{id}/` | Частичное обновление | Только авторизованные |
| DELETE | `/api/wells/{id}/` | Удаление скважины | Только авторизованные |
| GET | `/api/wells/{id}/telemetry/` | Телеметрия скважины | Все |
| GET | `/api/wells/statistics/` | Статистика по скважинам | Все |

## 🎓 Ключевые концепции для начинающих

### 1. **ViewSet vs APIView**
- **APIView** — для отдельных эндпоинтов
- **ViewSet** — для группы связанных эндпоинтов (как в REST)

### 2. **QuerySet** — ленивые запросы
- Не выполняется сразу в БД
- "Собирается" из фильтров и условий
- Выполняется только при необходимости (например, при `count()` или итерации)

### 3. **Сериализатор** — мост между Django и JSON
- **Валидация**: проверяет корректность данных
- **Преобразование**: Django Model ↔ Python dict ↔ JSON
- **Вложенные отношения**: может включать связанные объекты

### 4. **Декоратор `@action`**
- Превращает метод класса в эндпоинт
- `detail=True` → для одного объекта
- `detail=False` → для коллекции

### 5. **Параметры запроса (Query Parameters)**
- Часть URL после `?`
- `?ключ=значение&ключ2=значение2`
- Для фильтрации, сортировки, пагинации

### 6. **Lookup-выражения Django**
- `field__exact` — точное совпадение
- `field__gte` — больше или равно (≥)
- `field__lte` — меньше или равно (≤)
- `field__contains` — содержит подстроку
- `field__in` — в списке значений

## 🚀 Практические советы

### Для отладки:
```python
# Добавьте в get_queryset():
print("Параметры запроса:", dict(self.request.query_params))
print("SQL запрос:", str(queryset.query))
```

### Для расширения функционала:
1. **Добавьте пагинацию**:
```python
from rest_framework.pagination import PageNumberPagination

class WellPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    
class WellViewSet(viewsets.ModelViewSet):
    pagination_class = WellPagination
```

2. **Добавьте поиск**:
```python
from rest_framework import filters

class WellViewSet(viewsets.ModelViewSet):
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'location', 'description']
```

3. **Добавьте кэширование**:
```python
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class WellViewSet(viewsets.ModelViewSet):
    @method_decorator(cache_page(60 * 5))  # Кэш на 5 минут
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
```

## 📝 Итог

**WellViewSet** — это мощный, но понятный класс, который:
1. **Автоматически** создаёт полный REST API
2. **Гибко настраивается** через переопределение методов
3. **Расширяется** кастомными действиями
4. **Защищает данные** через систему прав доступа
5. **Эффективно работает** с БД через QuerySet

Это отличная основа для любого REST API в Django, которую можно адаптировать под конкретные нужды проекта.
