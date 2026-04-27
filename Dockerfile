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

# ВЫПОЛНЯЕМ МИГРАЦИИ (ЭТО САМОЕ ГЛАВНОЕ!)
RUN python manage.py makemigrations
RUN python manage.py migrate

EXPOSE 8000

# Запускаем gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]