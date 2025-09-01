FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    libssl-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя приложения
RUN useradd --create-home --shell /bin/bash app

# Рабочая директория
WORKDIR /app

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY --chown=app:app . .

# Создание необходимых директорий
RUN mkdir -p uploads downloads logs templates && \
    chown -R app:app /app && \
    chmod -R 755 /app

# Пользователь приложения
USER app

# Переменные окружения
ENV FLASK_APP=main.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health?format=json || exit 1

# Порт
EXPOSE 5000

# Запуск
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "300", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "main:app"]