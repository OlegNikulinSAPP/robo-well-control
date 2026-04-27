FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Создаём временную папку для статики
RUN mkdir -p /app/static

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]