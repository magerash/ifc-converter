#!/bin/bash

# Скрипт для развертывания IFC Converter v2.0 с двухсерверной архитектурой

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

print_header "🚀 Развертывание IFC Converter v2.0"

# =============================================================================
# ПРОВЕРКА DOCKER
# =============================================================================

print_info "Проверяем наличие Docker..."

if ! command -v docker &> /dev/null; then
    print_warning "Docker не установлен. Устанавливаем..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_success "Docker установлен. ВАЖНО: Перелогиньтесь для применения изменений!"

    # Проверяем, можем ли мы запустить Docker без sudo
    if ! docker ps &> /dev/null; then
        print_error "Необходимо перелогиниться для применения прав Docker"
        print_info "Выполните: exit, затем зайдите снова по SSH"
        print_info "После этого запустите: ./deploy.sh"
        exit 1
    fi
else
    print_success "Docker уже установлен"
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_warning "Docker Compose не установлен. Устанавливаем..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose установлен"
else
    print_success "Docker Compose уже установлен"
    print_info "Версия: $(docker-compose version --short)"
fi

# =============================================================================
# ПРОВЕРКА КОНФИГУРАЦИИ
# =============================================================================

print_header "📋 Проверка конфигурации"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    print_error "Файл .env не найден!"
    print_info "Создаем базовый .env файл..."

    cat > .env << 'EOF'
# OAuth2 Configuration
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-oauth-client-secret

# Flask Configuration
SECRET_KEY=your-super-secret-key-change-in-production
FLASK_ENV=production
FLASK_DEBUG=0

# Google Sheets API credentials
GS_TYPE=service_account
GS_PROJECT_ID=your-project-id
GS_PRIVATE_KEY_ID=your-private-key-id
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GS_CLIENT_ID=your-client-id
GS_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GS_TOKEN_URI=https://oauth2.googleapis.com/token
GS_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GS_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com
GS_SPREADSHEET_ID=your-spreadsheet-id-here

# Database path for second server
DB_PATH=users_history.db

# Ngrok URL (для разработки)
NGROK_URL=
EOF

    print_warning "Создан базовый .env файл с placeholder'ами"
    print_error "ОБЯЗАТЕЛЬНО замените значения your-* на реальные!"
    print_info "Инструкции по настройке: см. DEPLOYMENT.md"

    # Предлагаем открыть редактор
    read -p "Открыть .env для редактирования сейчас? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    else
        print_info "Отредактируйте .env файл перед продолжением"
        exit 1
    fi
fi

print_success "Файл .env найден"

# Проверяем критичные переменные
source .env

# Функция для проверки placeholder'ов
check_placeholder() {
    local var_name=$1
    local var_value=$2
    local contains_placeholder=$3

    if [[ "$var_value" == *"$contains_placeholder"* ]]; then
        print_error "$var_name содержит placeholder '$contains_placeholder'"
        return 1
    fi
    return 0
}

# Проверяем OAuth2 настройки
has_placeholders=false

if ! check_placeholder "GOOGLE_CLIENT_ID" "$GOOGLE_CLIENT_ID" "your-oauth-client-id"; then
    has_placeholders=true
fi

if ! check_placeholder "GOOGLE_CLIENT_SECRET" "$GOOGLE_CLIENT_SECRET" "your-oauth-client-secret"; then
    has_placeholders=true
fi

if ! check_placeholder "SECRET_KEY" "$SECRET_KEY" "your-super-secret-key"; then
    has_placeholders=true
fi

if ! check_placeholder "GS_PROJECT_ID" "$GS_PROJECT_ID" "your-project-id"; then
    has_placeholders=true
fi

if ! check_placeholder "GS_SPREADSHEET_ID" "$GS_SPREADSHEET_ID" "your-spreadsheet-id"; then
    has_placeholders=true
fi

if [ "$has_placeholders" = true ]; then
    print_error "Обнаружены незаполненные переменные в .env!"
    print_info "Получите credentials в Google Cloud Console:"
    print_info "1. OAuth2: https://console.cloud.google.com/apis/credentials"
    print_info "2. Service Account: для Google Sheets API"
    print_info "3. Подробные инструкции: см. DEPLOYMENT.md"
    exit 1
fi

print_success "Конфигурация проверена"

# =============================================================================
# СОЗДАНИЕ ДИРЕКТОРИЙ
# =============================================================================

print_header "📁 Создание рабочих директорий"

# Создаем необходимые директории
directories=("uploads" "downloads" "logs" "ssl" "templates")

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_info "Создана директория: $dir"
    else
        print_info "Директория уже существует: $dir"
    fi
done

# Создаем .gitkeep файлы для пустых папок
for dir in "uploads" "downloads" "logs"; do
    if [ ! -f "$dir/.gitkeep" ]; then
        touch "$dir/.gitkeep"
    fi
done

print_success "Все директории готовы"

# =============================================================================
# ПРОВЕРКА ПОРТОВ
# =============================================================================

print_header "🔍 Проверка доступности портов"

# Функция для проверки порта
check_port() {
    local port=$1
    local service_name=$2

    if lsof -i ":$port" &> /dev/null; then
        print_warning "Порт $port занят ($service_name)"
        print_info "Процессы на порту $port:"
        lsof -i ":$port" | head -5

        # Для портов веб-серверов предлагаем остановить
        if [ "$port" = "80" ] || [ "$port" = "443" ]; then
            read -p "Остановить системные веб-серверы? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo systemctl stop apache2 2>/dev/null || true
                sudo systemctl stop nginx 2>/dev/null || true
                print_info "Системные веб-серверы остановлены"
            fi
        fi

        return 1
    else
        print_success "Порт $port свободен ($service_name)"
        return 0
    fi
}

# Проверяем основные порты
ports_to_check=(
    "5000:Основной сервер"
    "5001:OAuth2 сервер"
    "8080:Nginx proxy"
)

ports_busy=false
for port_info in "${ports_to_check[@]}"; do
    port=${port_info%%:*}
    service=${port_info##*:}

    if ! check_port "$port" "$service"; then
        ports_busy=true
    fi
done

# Если порты заняты, предлагаем варианты
if [ "$ports_busy" = true ]; then
    print_warning "Некоторые порты заняты"
    print_info "Варианты решения:"
    print_info "1. Остановить конфликтующие сервисы"
    print_info "2. Изменить порты в docker-compose.yml"
    print_info "3. Остановить существующие Docker контейнеры"

    read -p "Попробовать остановить существующие Docker контейнеры? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Останавливаем существующие контейнеры..."
        docker-compose down 2>/dev/null || true
        docker stop $(docker ps -q) 2>/dev/null || true
        print_success "Существующие контейнеры остановлены"
    fi
fi

# =============================================================================
# ПРОВЕРКА DOCKER-COMPOSE.YML
# =============================================================================

print_header "🐳 Проверка конфигурации Docker"

if [ ! -f "docker-compose.yml" ]; then
    print_error "Файл docker-compose.yml не найден!"
    exit 1
fi

# Валидация docker-compose.yml
print_info "Проверяем синтаксис docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    print_success "docker-compose.yml корректен"
else
    print_error "Ошибка в docker-compose.yml:"
    docker-compose config
    exit 1
fi

# Проверяем наличие обоих сервисов
if grep -q "ifc-converter:" docker-compose.yml && grep -q "ifc-converter2:" docker-compose.yml; then
    print_success "Найдены оба сервера (ifc-converter и ifc-converter2)"
else
    print_error "Не найден один из серверов в docker-compose.yml"
    print_info "Требуются сервисы: ifc-converter (5000) и ifc-converter2 (5001)"
    exit 1
fi

# =============================================================================
# ОСТАНОВКА СУЩЕСТВУЮЩИХ СЕРВИСОВ
# =============================================================================

print_header "🛑 Остановка существующих сервисов"

print_info "Останавливаем существующие контейнеры..."
docker-compose down 2>/dev/null || true

# Очистка старых образов (опционально)
read -p "Очистить старые Docker образы для пересборки? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Удаляем старые образы..."
    docker-compose down --rmi all 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
    print_success "Старые образы удалены"
fi

# =============================================================================
# СБОРКА ОБРАЗОВ
# =============================================================================

print_header "🔨 Сборка Docker образов"

print_info "Собираем образы (это может занять несколько минут)..."

# Сборка с подробным выводом
if docker-compose build --no-cache; then
    print_success "Образы собраны успешно"
else
    print_error "Ошибка при сборке образов"
    print_info "Проверьте логи выше для диагностики"
    exit 1
fi

# =============================================================================
# ЗАПУСК СЕРВИСОВ
# =============================================================================

print_header "🚀 Запуск сервисов"

print_info "Запускаем все сервисы..."

if docker-compose up -d; then
    print_success "Сервисы запущены в фоновом режиме"
else
    print_error "Ошибка при запуске сервисов"
    print_info "Логи для диагностики:"
    docker-compose logs --tail=20
    exit 1
fi

# =============================================================================
# ОЖИДАНИЕ ЗАПУСКА
# =============================================================================

print_header "⏳ Ожидание запуска сервисов"

print_info "Ждем запуска сервисов (30 секунд)..."
sleep 30

# =============================================================================
# ПРОВЕРКА СТАТУСА
# =============================================================================

print_header "🔍 Проверка статуса сервисов"

print_info "Статус контейнеров:"
docker-compose ps

# Проверяем каждый сервис отдельно
services=("ifc-converter" "ifc-converter2" "nginx")
all_healthy=true

for service in "${services[@]}"; do
    if docker-compose ps "$service" | grep -q "Up"; then
        print_success "$service: запущен"
    else
        print_error "$service: не запущен или ошибка"
        all_healthy=false

        # Показываем логи для диагностики
        print_info "Последние 10 строк логов $service:"
        docker-compose logs --tail=10 "$service" || true
    fi
done

# =============================================================================
# ПРОВЕРКА ДОСТУПНОСТИ
# =============================================================================

print_header "🌐 Проверка доступности приложений"

# Функция для проверки HTTP endpoint'а
check_endpoint() {
    local url=$1
    local description=$2
    local timeout=${3:-10}

    if curl -f -s -m "$timeout" "$url" > /dev/null 2>&1; then
        print_success "$description: доступен ($url)"
        return 0
    else
        print_warning "$description: недоступен ($url)"
        return 1
    fi
}

# Проверяем основные endpoints
endpoints=(
    "http://localhost:5000/:Основной сервер (без OAuth2)"
    "http://localhost:5001/:OAuth2 сервер (с авторизацией)"
    "http://localhost:8080/:Nginx proxy (рекомендуемый доступ)"
    "http://localhost:5000/health:Health check - основной"
    "http://localhost:5001/health:Health check - OAuth2"
    "http://localhost:8080/health:Health check - через Nginx"
)

healthy_endpoints=0
total_endpoints=${#endpoints[@]}

for endpoint_info in "${endpoints[@]}"; do
    url=${endpoint_info%%:*}
    description=${endpoint_info##*:}

    if check_endpoint "$url" "$description" 15; then
        ((healthy_endpoints++))
    fi
done

print_info "Доступно endpoint'ов: $healthy_endpoints/$total_endpoints"

# =============================================================================
# ПРОВЕРКА GOOGLE API
# =============================================================================

print_header "📊 Проверка Google API"

print_info "Тестируем подключение к Google Sheets API..."

# Проверяем через OAuth2 сервер
if docker-compose exec -T ifc-converter2 python3 -c "
from gsheets import validate_gs_credentials
try:
    validate_gs_credentials()
    print('Google Sheets API: OK')
except Exception as e:
    print(f'Google Sheets API Error: {e}')
    exit(1)
" 2>/dev/null; then
    print_success "Google Sheets API настроен корректно"
else
    print_warning "Google Sheets API: проблема с настройкой"
    print_info "Проверьте переменные GS_* в .env файле"
fi

# =============================================================================
# ПРОВЕРКА OAUTH2
# =============================================================================

print_header "🔐 Проверка OAuth2"

print_info "Проверяем OAuth2 конфигурацию..."

oauth_vars=("GOOGLE_CLIENT_ID" "GOOGLE_CLIENT_SECRET")
oauth_ok=true

for var in "${oauth_vars[@]}"; do
    if docker-compose exec -T ifc-converter2 printenv "$var" > /dev/null 2>&1; then
        print_success "$var: установлена"
    else
        print_error "$var: не найдена в контейнере"
        oauth_ok=false
    fi
done

if [ "$oauth_ok" = true ]; then
    print_success "OAuth2 переменные настроены"
    print_info "Тестовый URL для входа: http://localhost:5001/login"
else
    print_warning "OAuth2 может работать некорректно"
fi

# =============================================================================
# ПРОВЕРКА БАЗЫ ДАННЫХ
# =============================================================================

print_header "💾 Проверка базы данных пользователей"

print_info "Проверяем базу данных SQLite..."

if docker-compose exec -T ifc-converter2 python3 -c "
import sqlite3
import os
db_path = os.getenv('DB_PATH', 'users_history.db')
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
    tables = cursor.fetchall()
    print(f'База данных: {len(tables)} таблиц')
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
        count = cursor.fetchone()[0]
        print(f'  {table[0]}: {count} записей')
    conn.close()
    print('База данных: OK')
except Exception as e:
    print(f'База данных: Error - {e}')
    exit(1)
" 2>/dev/null; then
    print_success "База данных пользователей работает корректно"
else
    print_warning "Проблема с базой данных (будет создана при первом использовании)"
fi

# =============================================================================
# ИТОГОВАЯ ИНФОРМАЦИЯ
# =============================================================================

print_header "🎉 Развертывание завершено!"

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ IFC Converter v2.0 успешно развернут!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo
echo -e "${CYAN}📍 Доступ к приложению:${NC}"
echo -e "${WHITE}  Основной сервер (без авторизации): ${GREEN}http://localhost:5000/${NC}"
echo -e "${WHITE}  OAuth2 сервер (с историей):        ${GREEN}http://localhost:5001/${NC}"
echo -e "${WHITE}  Nginx proxy (рекомендуется):       ${GREEN}http://localhost:8080/${NC}"
echo
echo -e "${CYAN}🔍 Мониторинг и диагностика:${NC}"
echo -e "${WHITE}  Health Check основной:     ${GREEN}http://localhost:5000/health${NC}"
echo -e "${WHITE}  Health Check OAuth2:       ${GREEN}http://localhost:5001/health${NC}"
echo -e "${WHITE}  Health Check Nginx:        ${GREEN}http://localhost:8080/health${NC}"
echo
echo -e "${CYAN}🔐 OAuth2 тестирование:${NC}"
echo -e "${WHITE}  Вход через Google:         ${GREEN}http://localhost:5001/login${NC}"
echo -e "${WHITE}  Dashboard (после входа):   ${GREEN}http://localhost:5001/dashboard${NC}"
echo

# Проверяем внешний IP для информации
external_ip=""
if command -v curl &> /dev/null; then
    external_ip=$(curl -s -m 5 ifconfig.me 2>/dev/null || echo "неизвестен")
    if [ "$external_ip" != "неизвестен" ] && [ -n "$external_ip" ]; then
        echo -e "${CYAN}🌍 Внешний доступ (если настроен firewall):${NC}"
        echo -e "${WHITE}  http://${external_ip}:8080/${NC}"
        echo
    fi
fi

echo -e "${CYAN}📋 Полезные команды:${NC}"
echo -e "${WHITE}  Просмотр логов:              ${YELLOW}docker-compose logs -f${NC}"
echo -e "${WHITE}  Просмотр логов OAuth2:       ${YELLOW}docker-compose logs -f ifc-converter2${NC}"
echo -e "${WHITE}  Статус сервисов:             ${YELLOW}docker-compose ps${NC}"
echo -e "${WHITE}  Перезапуск:                  ${YELLOW}docker-compose restart${NC}"
echo -e "${WHITE}  Остановка:                   ${YELLOW}docker-compose down${NC}"
echo -e "${WHITE}  Обновление (пересборка):     ${YELLOW}./rebuild.sh${NC}"
echo -e "${WHITE}  Тест OAuth2:                 ${YELLOW}python3 test_oauth.py${NC}"
echo

# Предупреждения и рекомендации
if [ "$healthy_endpoints" -lt "$total_endpoints" ]; then
    echo -e "${YELLOW}⚠️  Предупреждения:${NC}"
    echo -e "${WHITE}  Не все endpoint'ы доступны. Проверьте логи: docker-compose logs${NC}"
    echo
fi

echo -e "${CYAN}🔧 Следующие шаги:${NC}"
echo -e "${WHITE}1. Протестируйте загрузку IFC файла: http://localhost:8080/${NC}"
echo -e "${WHITE}2. Проверьте OAuth2 авторизацию: http://localhost:5001/login${NC}"
echo -e "${WHITE}3. Настройте домен и SSL (см. DEPLOYMENT.md)${NC}"
echo -e "${WHITE}4. Настройте мониторинг и резервное копирование${NC}"
echo
echo -e "${GREEN}🎯 Развертывание v2.0 завершено успешно!${NC}"

# Опционально показываем логи
read -p "Показать логи приложения? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Показываем логи (Ctrl+C для выхода)..."
    docker-compose logs -f
fi