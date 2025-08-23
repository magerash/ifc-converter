#!/bin/bash

# Скрипт для развертывания IFC Converter на сервере

set -e

echo "🚀 Начинаем развертывание IFC Converter..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Устанавливаем..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker установлен. Перелогиньтесь для применения изменений."
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Устанавливаем..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose установлен."
fi

# Создаем необходимые директории
echo "📁 Создаем рабочие директории..."
mkdir -p uploads downloads logs ssl

# Создаем .gitkeep файлы для пустых папок
touch uploads/.gitkeep
touch downloads/.gitkeep
touch logs/.gitkeep

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте файл .env с настройками Google API."
    echo "   Пример содержимого:"
    cat << EOF
# Google Sheets API credentials
GS_TYPE=service_account
GS_PROJECT_ID=your-project-id
GS_PRIVATE_KEY_ID=your-private-key-id
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY_HERE\\n-----END PRIVATE KEY-----\\n"
GS_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GS_CLIENT_ID=your-client-id
GS_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GS_TOKEN_URI=https://oauth2.googleapis.com/token
GS_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GS_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com
GS_SPREADSHEET_ID=your-spreadsheet-id-here
EOF
    exit 1
fi

# Останавливаем существующие контейнеры (если есть)
echo "🛑 Останавливаем существующие контейнеры..."
docker-compose down || true

# Собираем образ
echo "🔨 Собираем Docker образ..."
docker-compose build

# Запускаем сервисы
echo "🚀 Запускаем сервисы..."
docker-compose up -d

# Ждем запуска
echo "⏳ Ждем запуска сервисов..."
sleep 10

# Проверяем статус
echo "🔍 Проверяем статус сервисов..."
docker-compose ps

# Проверяем доступность приложения
echo "🌐 Проверяем доступность приложения..."
if curl -f http://localhost:5000/ > /dev/null 2>&1; then
    echo "✅ Приложение успешно запущено!"
    echo "🌐 Доступно по адресу: http://localhost:5000/"

    # Если настроен nginx
    if docker-compose ps nginx | grep -q "Up"; then
        echo "🌐 Также доступно через Nginx: http://localhost/"
    fi
else
    echo "❌ Приложение не отвечает. Проверьте логи:"
    echo "   docker-compose logs ifc-converter"
fi

echo ""
echo "📋 Полезные команды:"
echo "   Просмотр логов:      docker-compose logs -f"
echo "   Перезапуск:          docker-compose restart"
echo "   Остановка:           docker-compose down"
echo "   Обновление образа:   docker-compose build --no-cache"
echo ""
echo "🎉 Развертывание завершено!"