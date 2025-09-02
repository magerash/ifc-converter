#!/bin/bash

# Простое развертывание IFC Converter v1.1 на порту 5000

set -e

echo "🚀 Развертывание IFC Converter v1.1..."

# Установка Docker (если нет)
if ! command -v docker &> /dev/null; then
    echo "Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "⚠️ Перелогиньтесь после установки Docker"
    exit 1
fi

# Установка Docker Compose (если нет)
if ! command -v docker-compose &> /dev/null; then
    echo "Устанавливаем Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Создание директорий
mkdir -p uploads downloads logs

# Проверка .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Создайте .env файл с настройками Google API:"
    echo ""
    cat << 'EOF'
# OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Flask
SECRET_KEY=your-secret-key

# Google Sheets API
GS_TYPE=service_account
GS_PROJECT_ID=your-project-id
GS_PRIVATE_KEY_ID=your-key-id
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_KEY\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=service@project.iam.gserviceaccount.com
GS_CLIENT_ID=your-client-id
GS_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GS_TOKEN_URI=https://oauth2.googleapis.com/token
GS_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GS_CLIENT_X509_CERT_URL=your-cert-url
GS_SPREADSHEET_ID=your-spreadsheet-id
EOF
    exit 1
fi

# Остановка старых контейнеров
docker-compose down 2>/dev/null || true

# Сборка и запуск
echo "Собираем образ..."
docker-compose build --no-cache

echo "Запускаем контейнер..."
docker-compose up -d

# Ожидание запуска
sleep 5

# Проверка
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Приложение запущено: http://localhost:5000/"
else
    echo "❌ Ошибка запуска. Проверьте логи: docker-compose logs -f"
fi

echo ""
echo "Команды управления:"
echo "  Логи:      docker-compose logs -f"
echo "  Остановка: docker-compose down"
echo "  Статус:    docker-compose ps"