FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Удаляем проблемные файлы
RUN find . -name "swagger.py" -type f -delete
RUN pip install --upgrade requests

# Создаём папку для статики
RUN mkdir -p /app/static

EXPOSE 8000

# Миграции и запуск — ВСЁ В ОДНОЙ КОМАНДЕ
CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]