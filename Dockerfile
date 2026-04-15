FROM python:3.11-slim

# Установка git и pip-tools (обновляем pip)
RUN apt-get update && apt-get install -y git && pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
