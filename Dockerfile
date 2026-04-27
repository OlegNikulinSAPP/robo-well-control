FROM python:3.12-slim

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём папку для статики (как было в ваших логах)
RUN mkdir -p /app/static

# Указываем порт (важно для платформы)
EXPOSE 8000

# Команда запуска
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]