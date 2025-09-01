#!/bin/bash

# Простой запуск development окружения с ngrok

echo "🔧 Запуск development с ngrok..."

# Проверка ngrok
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok не установлен"
    echo "Скачайте с https://ngrok.com/download"
    exit 1
fi

# Останавливаем существующие ngrok процессы
pkill -f "ngrok http" || true
sleep 2

# Проверка и настройка authtoken
if [ -f .env ]; then
    source .env
    if [ -n "$NGROK_AUTH_TOKEN" ]; then
        echo "🔑 Настраиваем ngrok authtoken..."
        ngrok config add-authtoken "$NGROK_AUTH_TOKEN" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ ngrok authtoken настроен"
        else
            echo "❌ Ошибка настройки ngrok authtoken"
            echo "Проверьте правильность токена в переменной NGROK_AUTH_TOKEN"
            exit 1
        fi
    else
        echo "⚠️ NGROK_AUTH_TOKEN не найден в .env"
        echo "Добавьте в .env: NGROK_AUTH_TOKEN=ваш_токен_от_ngrok"
        exit 1
    fi
else
    echo "❌ Файл .env не найден"
    echo "Создайте .env файл с переменной NGROK_AUTH_TOKEN"
    exit 1
fi

# Запуск ngrok в отдельном терминале или с nohup
echo "Запускаем ngrok на порту 5000..."
# Используем nohup для запуска в фоне с перенаправлением вывода
nohup ngrok http 5000 > ngrok.log 2>&1 &
NGROK_PID=$!

# Ждем запуска ngrok
sleep 7

# Получаем URL от ngrok с улучшенной обработкой ошибок
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    if tunnels:
        # Ищем HTTPS туннель (он более стабильный)
        for tunnel in tunnels:
            if tunnel.get('proto') == 'https':
                print(tunnel['public_url'])
                break
        else:
            print(tunnels[0]['public_url'])
    else:
        print('')
except Exception as e:
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
    echo ""
    echo "📝 Логи ngrok в файле: ngrok.log"

else
    echo "❌ Не удалось получить ngrok URL"
    echo "Проверьте логи: cat ngrok.log"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

# Проверяем, что ngrok все еще работает
sleep 2
if ! curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
    echo "❌ ngrok перестал работать после получения URL"
    echo "Проверьте логи: cat ngrok.log"
    exit 1
fi

echo "✅ ngrok успешно запущен и работает"
echo "🚀 Запускаем приложение..."

# Запуск приложения в foreground
python3 main.py

# При завершении приложения убиваем ngrok
echo "🛑 Останавливаем ngrok..."
kill $NGROK_PID 2>/dev/null