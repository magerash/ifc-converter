#!/bin/bash

# =============================================================================
# IFC Converter - Development Environment with ngrok
# =============================================================================

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_header() {
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# =============================================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# =============================================================================

print_header "🔍 Проверка зависимостей"

# Проверка Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python установлен: $PYTHON_VERSION"
else
    print_error "Python 3 не установлен"
    exit 1
fi

# Проверка pip
if command -v pip3 &> /dev/null; then
    print_success "pip3 установлен"
else
    print_error "pip3 не установлен"
    exit 1
fi

# Проверка ngrok
if command -v ngrok &> /dev/null; then
    NGROK_VERSION=$(ngrok version | head -n 1)
    print_success "ngrok установлен: $NGROK_VERSION"
else
    print_error "ngrok не установлен"
    print_info "Установите с https://ngrok.com/download"

    # Предложение автоматической установки
    read -p "Попытаться установить ngrok автоматически? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Скачиваем ngrok..."

        # Определяем OS и архитектуру
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        ARCH=$(uname -m)

        if [[ "$ARCH" == "x86_64" ]]; then
            ARCH="amd64"
        elif [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
            ARCH="arm64"
        fi

        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-${OS}-${ARCH}.tgz"

        wget -q "$NGROK_URL" -O ngrok.tgz
        tar -xzf ngrok.tgz
        sudo mv ngrok /usr/local/bin/
        rm ngrok.tgz

        print_success "ngrok установлен"
    else
        exit 1
    fi
fi

# =============================================================================
# ПРОВЕРКА И СОЗДАНИЕ .env
# =============================================================================

print_header "📋 Проверка конфигурации"

if [ ! -f .env ]; then
    print_warning ".env файл не найден. Создаем..."

    cat > .env << 'EOF'
# OAuth2 Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here

# Flask Configuration
SECRET_KEY=dev-secret-key-$(openssl rand -hex 32)
FLASK_ENV=development
FLASK_DEBUG=1

# Ngrok URL (обновляется автоматически)
NGROK_URL=

# Google Sheets API (опционально)
GS_SPREADSHEET_ID=
GS_PROJECT_ID=
GS_CLIENT_EMAIL=
EOF

    print_success "Создан .env файл"
    print_warning "Обязательно заполните GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET!"

    # Открываем редактор
    read -p "Открыть .env для редактирования? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
fi

# Загружаем переменные
source .env

# Проверяем критичные переменные
if [[ "$GOOGLE_CLIENT_ID" == "your-client-id.apps.googleusercontent.com" ]]; then
    print_error "GOOGLE_CLIENT_ID не настроен в .env"
    print_info "Получите credentials в https://console.cloud.google.com/"
    exit 1
fi

if [[ "$GOOGLE_CLIENT_SECRET" == "your-client-secret-here" ]]; then
    print_error "GOOGLE_CLIENT_SECRET не настроен в .env"
    exit 1
fi

print_success "OAuth2 credentials настроены"

# =============================================================================
# УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ
# =============================================================================

print_header "📦 Проверка Python зависимостей"

# Проверяем виртуальное окружение
if [ -d "venv" ]; then
    print_info "Активируем виртуальное окружение..."
    source venv/bin/activate
else
    print_info "Создаем виртуальное окружение..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Устанавливаем/обновляем зависимости
print_info "Устанавливаем зависимости..."
pip install -q --upgrade pip
pip install -q -r requirements.txt 2>/dev/null || {
    print_warning "requirements.txt не найден или содержит ошибки"
    print_info "Устанавливаем базовые зависимости..."
    pip install -q flask authlib requests python-dotenv gunicorn
}

# Дополнительные зависимости для тестирования
pip install -q colorama 2>/dev/null

print_success "Зависимости установлены"

# =============================================================================
# ЗАПУСК NGROK
# =============================================================================

print_header "🌐 Запуск ngrok туннеля"

# Проверяем, не запущен ли уже ngrok
NGROK_RUNNING=false
if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
    print_warning "ngrok уже запущен"
    NGROK_RUNNING=true

    # Получаем текущий URL
    NGROK_URL=$(curl -s localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels'):
        print(data['tunnels'][0]['public_url'])
except: pass
")
else
    # Запускаем ngrok
    print_info "Запускаем ngrok на порту 5001..."
    ngrok http 5001 > /dev/null 2>&1 &
    NGROK_PID=$!

    # Ждем запуска
    sleep 4

    # Получаем публичный URL
    NGROK_URL=$(curl -s localhost:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('tunnels'):
        print(data['tunnels'][0]['public_url'])
except: pass
")
fi

if [ -z "$NGROK_URL" ]; then
    print_error "Не удалось получить ngrok URL"
    print_info "Проверьте логи: http://localhost:4040"
    exit 1
fi

print_success "ngrok URL: $NGROK_URL"

# =============================================================================
# ОБНОВЛЕНИЕ .env
# =============================================================================

print_info "Обновляем .env файл..."

# Обновляем NGROK_URL в .env
if grep -q "NGROK_URL=" .env; then
    # macOS и Linux совместимый sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|NGROK_URL=.*|NGROK_URL=$NGROK_URL|" .env
    else
        sed -i "s|NGROK_URL=.*|NGROK_URL=$NGROK_URL|" .env
    fi
else
    echo "NGROK_URL=$NGROK_URL" >> .env
fi

print_success ".env обновлен"

# =============================================================================
# ИНСТРУКЦИИ ДЛЯ GOOGLE CONSOLE
# =============================================================================

print_header "📋 Настройка Google OAuth2"

echo -e "${YELLOW}ВАЖНО! Обновите настройки в Google Console:${NC}"
echo
echo -e "${WHITE}1. Откройте: ${CYAN}https://console.cloud.google.com/apis/credentials${NC}"
echo -e "${WHITE}2. Выберите ваш OAuth 2.0 Client ID${NC}"
echo -e "${WHITE}3. Добавьте в Authorized JavaScript origins:${NC}"
echo -e "   ${GREEN}$NGROK_URL${NC}"
echo -e "   ${GREEN}http://localhost:5001${NC}"
echo
echo -e "${WHITE}4. Добавьте в Authorized redirect URIs:${NC}"
echo -e "   ${GREEN}$NGROK_URL/auth/callback${NC}"
echo -e "   ${GREEN}http://localhost:5001/auth/callback${NC}"
echo
echo -e "${WHITE}5. Сохраните изменения${NC}"
echo

read -p "Нажмите Enter после обновления настроек в Google Console..."

# =============================================================================
# СОЗДАНИЕ ДИРЕКТОРИЙ
# =============================================================================

print_header "📁 Подготовка директорий"

# Создаем необходимые папки
mkdir -p uploads downloads logs templates

print_success "Директории созданы"

# =============================================================================
# ЗАПУСК FLASK
# =============================================================================

print_header "🚀 Запуск Flask приложения"

# Экспортируем переменные
export NGROK_URL=$NGROK_URL
export FLASK_ENV=development
export FLASK_DEBUG=1

echo
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ ПРИЛОЖЕНИЕ ГОТОВО К РАБОТЕ!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo
echo -e "${WHITE}Локальный доступ:  ${CYAN}http://localhost:5001${NC}"
echo -e "${WHITE}Публичный доступ:  ${CYAN}$NGROK_URL${NC}"
echo
echo -e "${WHITE}Тестовые ссылки:${NC}"
echo -e "  Главная:         ${CYAN}$NGROK_URL/${NC}"
echo -e "  Вход:            ${CYAN}$NGROK_URL/login${NC}"
echo -e "  Health Check:    ${CYAN}$NGROK_URL/health${NC}"
echo
echo -e "${WHITE}Мониторинг:${NC}"
echo -e "  ngrok Dashboard: ${CYAN}http://localhost:4040${NC}"
echo -e "  Flask Logs:      ${CYAN}См. ниже${NC}"
echo
echo -e "${YELLOW}Для остановки нажмите Ctrl+C${NC}"
echo -e "${GREEN}============================================================${NC}"
echo

# Функция для корректной остановки
cleanup() {
    echo
    print_info "Останавливаем сервисы..."

    # Останавливаем Flask (если запущен через этот скрипт)
    if [ ! -z "$FLASK_PID" ]; then
        kill $FLASK_PID 2>/dev/null
    fi

    # Останавливаем ngrok (если был запущен этим скриптом)
    if [ ! -z "$NGROK_PID" ] && [ "$NGROK_RUNNING" = false ]; then
        kill $NGROK_PID 2>/dev/null
    fi

    print_success "Остановлено"
    exit 0
}

# Устанавливаем обработчик сигналов
trap cleanup INT TERM

# Запускаем Flask
python3 main.py &
FLASK_PID=$!

# Ждем завершения
wait $FLASK_PID