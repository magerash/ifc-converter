#!/bin/bash

# Простой запуск development окружения с ngrok

echo "🔧 Запуск development с ngrok..."

# Проверка ngrok
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok не установлен"
    echo "Скачайте с https://ngrok.com/download"
    exit 1
fi

# Проверка authtoken в .env
if [ -f .env ]; then
    source .env
    if [ -n "$NGROK_AUTH_TOKEN" ]; then
        ngrok config add-authtoken "$NGROK_AUTH_TOKEN"
        echo "✅ ngrok authtoken настроен"
    fi
fi

# Запуск ngrok в фоне
echo "Запускаем ngrok..."
ngrok http 5000 > /dev/null 2>&1 &
NGROK_PID=$!

# Ждем запуска ngrok
sleep 3

# Получаем URL от ngrok
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['tunnels'][0]['public_url'])
except:
    print('')
")

if [ -n "$NGROK_URL" ]; then
    echo "✅ ngrok URL: $NGROK_URL"

    # Обновляем .env файл
    if [ -f .env ]; then
        # Удаляем старую строку и добавляем новую
        grep -v "NGROK_URL=" .env > .env.tmp && mv .env.tmp .env
        echo "NGROK_URL=$NGROK_URL" >> .env
        echo "✅ .env обновлен"
    fi

    echo ""
    echo "📋 Настройте в Google Console:"
    echo "   Redirect URI: $NGROK_URL/auth/callback"
    echo ""
    echo "🌐 Приложение доступно: $NGROK_URL"
    echo "🔗 Тест OAuth2: $NGROK_URL/login"

else
    echo "❌ Не удалось получить ngrok URL"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

# Запуск приложения
echo ""
echo "Запускаем приложение..."
python3 main.py