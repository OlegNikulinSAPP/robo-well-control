FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Удаляем проблемные файлы
RUN find . -name "swagger.py" -type f -delete 2>/dev/null || true
RUN pip install --upgrade requests

# Создаём папки
RUN mkdir -p /app/static
RUN mkdir -p /app/staticfiles

# Миграции и сбор статики
RUN python manage.py makemigrations --noinput
RUN python manage.py migrate --noinput
RUN python manage.py collectstatic --noinput

EXPOSE 8000

RUN python manage.py ensure_admin

#CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py import_motors motor_models.xls && python manage.py import_pumps test_pumps.xlsx && python manage.py ensure_admin && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]