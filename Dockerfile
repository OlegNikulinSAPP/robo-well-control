FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Создаём директорию для статики (как в ваших логах)
RUN mkdir -p /app/static

# Команда запуска (теперь здесь!)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]