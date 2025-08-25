FROM python:3.11-slim

# Метаданные образа
LABEL maintainer="IFC Converter Team"
LABEL version="2.0.0"
LABEL description="IFC to CSV converter with OAuth2 authentication and user history"

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
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создание пользователя приложения (безопасность)
RUN useradd --create-home --shell /bin/bash app

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода приложения
COPY --chown=app:app . .

# Создание необходимых директорий с правильными правами
RUN mkdir -p uploads downloads logs templates \
    && chown -R app:app /app \
    && chmod -R 755 /app

# Переключение на пользователя приложения
USER app

# Установка переменных окружения
ENV FLASK_APP=main.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Health check для Docker
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health?format=json || exit 1

# Открытие порта
EXPOSE 5000

# Создание volume для постоянного хранения данных
VOLUME ["/app/uploads", "/app/downloads", "/app/logs"]

# Запуск приложения через Gunicorn для production
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--worker-class", "sync", \
     "--timeout", "300", \
     "--keep-alive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "main:app"]