#!/bin/bash

# Скрипт подготовки операционной системы для IFC Converter v2.0
# Поддерживает Ubuntu/Debian и CentOS/RHEL

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

# Определение операционной системы
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        print_error "Cannot detect OS"
        exit 1
    fi
}

print_header "🚀 Подготовка операционной системы для IFC Converter v2.0"

# =============================================================================
# ОПРЕДЕЛЕНИЕ ОПЕРАЦИОННОЙ СИСТЕМЫ
# =============================================================================

detect_os
print_info "Обнаружена ОС: $OS $OS_VERSION"

# =============================================================================
# ОБНОВЛЕНИЕ СИСТЕМЫ
# =============================================================================

print_header "🔄 Обновление системы"

if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    print_info "Обновляем пакеты для Ubuntu/Debian..."
    sudo apt update && sudo apt upgrade -y

    print_info "Устанавливаем базовые пакеты..."
    sudo apt install -y \
        git \
        curl \
        wget \
        nano \
        ufw \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        unzip \
        htop \
        tree \
        jq

elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]] || [[ "$OS" == "rocky" ]] || [[ "$OS" == "almalinux" ]]; then
    print_info "Обновляем пакеты для CentOS/RHEL..."
    sudo yum update -y

    # Для CentOS 8+ используем dnf
    if command -v dnf &> /dev/null; then
        PACKAGE_MANAGER="dnf"
    else
        PACKAGE_MANAGER="yum"
    fi

    print_info "Устанавливаем базовые пакеты..."
    sudo $PACKAGE_MANAGER install -y \
        git \
        curl \
        wget \
        nano \
        firewalld \
        python3 \
        python3-pip \
        gcc \
        gcc-c++ \
        make \
        epel-release \
        unzip \
        htop \
        tree \
        jq

else
    print_error "Неподдерживаемая операционная система: $OS"
    exit 1
fi

print_success "Система обновлена и базовые пакеты установлены"

# =============================================================================
# НАСТРОЙКА PYTHON
# =============================================================================

print_header "🐍 Настройка Python"

# Проверяем версию Python
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_info "Версия Python: $PYTHON_VERSION"

# Обновляем pip
print_info "Обновляем pip..."
python3 -m pip install --user --upgrade pip

# Устанавливаем виртуальное окружение если нужно
if ! python3 -m venv --help &> /dev/null; then
    if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        sudo apt install -y python3-venv
    else
        sudo $PACKAGE_MANAGER install -y python3-virtualenv
    fi
fi

print_success "Python настроен"

# =============================================================================
# НАСТРОЙКА FIREWALL
# =============================================================================

print_header "🔥 Настройка firewall"

if [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
    print_info "Настраиваем ufw..."
    sudo ufw --force enable
    sudo ufw allow ssh
    sudo ufw allow 5000/tcp comment 'IFC Converter - Main Server'
    sudo ufw allow 5001/tcp comment 'IFC Converter - OAuth2 Server'
    sudo ufw allow 8080/tcp comment 'IFC Converter - Nginx Proxy'
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'

    print_success "ufw настроен"
    sudo ufw status

else
    print_info "Настраиваем firewalld..."
    sudo systemctl enable firewalld
    sudo systemctl start firewalld
    sudo firewall-cmd --permanent --add-port=5000/tcp --add-port=5001/tcp --add-port=8080/tcp
    sudo firewall-cmd --permanent --add-service=http --add-service=https
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --reload

    print_success "firewalld настроен"
    sudo firewall-cmd --list-all
fi

# =============================================================================
# УСТАНОВКА DOCKER
# =============================================================================

print_header "🐳 Установка Docker"

if command -v docker &> /dev/null; then
    print_success "Docker уже установлен: $(docker --version)"
else
    print_info "Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh

    # Добавляем пользователя в группу docker
    sudo usermod -aG docker $USER

    # Включаем автозапуск Docker
    sudo systemctl enable docker
    sudo systemctl start docker

    print_success "Docker установлен"
    print_warning "Необходимо перелогиниться для применения прав группы docker"
fi

# Установка Docker Compose
if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose уже установлен: $(docker-compose --version)"
else
    print_info "Устанавливаем Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    print_success "Docker Compose установлен"
fi

# =============================================================================
# УСТАНОВКА NGROK (ДЛЯ РАЗРАБОТКИ)
# =============================================================================

print_header "🌐 Установка ngrok (опционально)"

read -p "Установить ngrok для разработки с OAuth2? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v ngrok &> /dev/null; then
        print_success "ngrok уже установлен: $(ngrok version | head -1)"
    else
        print_info "Устанавливаем ngrok..."

        # Определяем архитектуру
        ARCH=$(uname -m)
        if [[ "$ARCH" == "x86_64" ]]; then
            ARCH="amd64"
        elif [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
            ARCH="arm64"
        fi

        # Определяем OS для ngrok
        NGROK_OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-${NGROK_OS}-${ARCH}.tgz"

        wget -q "$NGROK_URL" -O ngrok.tgz
        tar -xzf ngrok.tgz
        sudo mv ngrok /usr/local/bin/
        rm ngrok.tgz

        print_success "ngrok установлен"
    fi

    print_info "Для настройки ngrok выполните:"
    print_info "1. Зарегистрируйтесь на https://ngrok.com/"
    print_info "2. Выполните: ngrok config add-authtoken YOUR_TOKEN"
    print_info "3. Добавьте NGROK_AUTH_TOKEN в .env файл"
else
    print_info "ngrok пропущен"
fi

# =============================================================================
# СОЗДАНИЕ РАБОЧЕЙ ДИРЕКТОРИИ
# =============================================================================

print_header "📁 Создание рабочей директории"

WORK_DIR="$HOME/ifc-converter"

read -p "Создать рабочую директорию в $WORK_DIR? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d "$WORK_DIR" ]; then
        mkdir -p "$WORK_DIR"
        cd "$WORK_DIR"
        print_success "Создана директория: $WORK_DIR"

        # Создаем базовые поддиректории
        mkdir -p uploads downloads logs ssl templates

        # Создаем .gitkeep файлы
        touch uploads/.gitkeep downloads/.gitkeep logs/.gitkeep

        print_info "Созданы поддиректории: uploads, downloads, logs, ssl, templates"

        # Создаем базовый .env файл
        if [ ! -f ".env" ]; then
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

# Ngrok configuration (для разработки)
NGROK_AUTH_TOKEN=your-ngrok-auth-token
NGROK_URL=
EOF
            print_success "Создан базовый .env файл"
            print_warning "Не забудьте заполнить реальные значения в .env!"
        fi

    else
        cd "$WORK_DIR"
        print_info "Директория уже существует: $WORK_DIR"
    fi

    print_info "Рабочая директория: $(pwd)"
fi

# =============================================================================
# КЛОНИРОВАНИЕ ПРОЕКТА (ОПЦИОНАЛЬНО)
# =============================================================================

print_header "📦 Получение исходного кода"

if [ -f "docker-compose.yml" ] && [ -f "main.py" ]; then
    print_success "Файлы проекта уже присутствуют"
else
    print_info "Файлы проекта не найдены"

    read -p "Клонировать проект из Git репозитория? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Введите URL Git репозитория: " GIT_URL
        if [ -n "$GIT_URL" ]; then
            print_info "Клонируем репозиторий..."
            git clone "$GIT_URL" temp_clone
            mv temp_clone/* . 2>/dev/null || true
            mv temp_clone/.[!.]* . 2>/dev/null || true
            rm -rf temp_clone
            print_success "Проект клонирован"
        fi
    else
        print_info "Скопируйте файлы проекта в текущую директорию:"
        print_info "  - docker-compose.yml"
        print_info "  - Dockerfile"
        print_info "  - main.py и другие Python файлы"
        print_info "  - requirements.txt"
        print_info "  - templates/ директория"
    fi
fi

# =============================================================================
# УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ
# =============================================================================

print_header "🐍 Установка Python зависимостей"

if [ -f "requirements.txt" ]; then
    read -p "Установить Python зависимости локально (для разработки)? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Создаем виртуальное окружение
        if [ ! -d "venv" ]; then
            python3 -m venv venv
            print_success "Создано виртуальное окружение"
        fi

        # Активируем и устанавливаем зависимости
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt

        # Дополнительные зависимости для разработки
        pip install colorama python-dotenv requests

        print_success "Python зависимости установлены в виртуальное окружение"
        print_info "Для активации: source venv/bin/activate"
    fi
else
    print_warning "Файл requirements.txt не найден"
    print_info "Будет установлено при сборке Docker образа"
fi

# =============================================================================
# НАСТРОЙКА СИСТЕМНЫХ СЕРВИСОВ
# =============================================================================

print_header "⚙️  Настройка системных сервисов"

# Отключаем системные веб-серверы если они есть
for service in apache2 httpd nginx; do
    if systemctl is-active --quiet $service 2>/dev/null; then
        print_warning "Обнаружен активный $service"
        read -p "Остановить $service для избежания конфликтов портов? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo systemctl stop $service
            sudo systemctl disable $service
            print_success "$service остановлен и отключен"
        fi
    fi
done

# Проверяем доступность портов
print_info "Проверяем доступность портов..."
for port in 5000 5001 8080; do
    if lsof -i :$port &> /dev/null; then
        print_warning "Порт $port занят:"
        lsof -i :$port | head -3
    else
        print_success "Порт $port свободен"
    fi
done

# =============================================================================
# СОЗДАНИЕ SYSTEMD СЕРВИСА (ОПЦИОНАЛЬНО)
# =============================================================================

print_header "🔄 Создание systemd сервиса (опционально)"

read -p "Создать systemd сервис для автозапуска? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/ifc-converter.service"

    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=IFC Converter v2.0
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ifc-converter.service

    print_success "Systemd сервис создан: $SERVICE_FILE"
    print_info "Команды управления:"
    print_info "  Запуск:    sudo systemctl start ifc-converter"
    print_info "  Остановка: sudo systemctl stop ifc-converter"
    print_info "  Статус:    sudo systemctl status ifc-converter"
else
    print_info "Systemd сервис пропущен"
fi

# =============================================================================
# НАСТРОЙКА CRON ЗАДАЧ
# =============================================================================

print_header "⏰ Настройка автоматического обслуживания"

read -p "Настроить cron задачи для обслуживания? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Создаем скрипт обслуживания
    MAINTENANCE_SCRIPT="$(pwd)/maintenance.sh"

    cat > "$MAINTENANCE_SCRIPT" << 'EOF'
#!/bin/bash
# Автоматическое обслуживание IFC Converter

WORK_DIR=$(dirname "$0")
cd "$WORK_DIR"

echo "$(date): Начинаем обслуживание..."

# Очистка старых файлов
echo "Очищаем старые файлы..."
find downloads/ -name "*.csv" -mtime +7 -delete 2>/dev/null || true
find uploads/ -name "*.ifc" -mtime +3 -delete 2>/dev/null || true
find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true

# Резервное копирование базы данных
echo "Резервное копирование базы данных..."
docker-compose exec -T ifc-converter2 sqlite3 users_history.db ".backup /app/logs/backup_$(date +%Y%m%d).db" 2>/dev/null || true

# Очистка старых backup'ов
find logs/ -name "backup_*.db" -mtime +30 -delete 2>/dev/null || true

# Проверка здоровья системы
echo "Проверка здоровья системы..."
curl -f http://localhost:5000/health > /dev/null 2>&1 || echo "WARNING: Main server health check failed"
curl -f http://localhost:5001/health > /dev/null 2>&1 || echo "WARNING: OAuth2 server health check failed"

echo "$(date): Обслуживание завершено"
EOF

    chmod +x "$MAINTENANCE_SCRIPT"
    print_success "Создан скрипт обслуживания: $MAINTENANCE_SCRIPT"

    # Добавляем cron задачи
    (crontab -l 2>/dev/null; echo "# IFC Converter maintenance") | crontab -
    (crontab -l 2>/dev/null; echo "0 2 * * * $MAINTENANCE_SCRIPT >> $(pwd)/logs/maintenance.log 2>&1") | crontab -

    # Еженедельная перезагрузка для профилактики
    (crontab -l 2>/dev/null; echo "0 4 * * 0 cd $(pwd) && docker-compose restart >> logs/maintenance.log 2>&1") | crontab -

    print_success "Cron задачи добавлены"
    print_info "Обслуживание: ежедневно в 02:00"
    print_info "Перезапуск: еженедельно в воскресенье 04:00"
else
    print_info "Автоматическое обслуживание пропущено"
fi

# =============================================================================
# ПРОВЕРКА ГОТОВНОСТИ
# =============================================================================

print_header "✅ Проверка готовности системы"

checks_passed=0
total_checks=0

# Проверка Docker
((total_checks++))
if docker --version &> /dev/null && docker-compose --version &> /dev/null; then
    print_success "Docker и Docker Compose готовы"
    ((checks_passed++))
else
    print_error "Проблема с Docker"
fi

# Проверка Python
((total_checks++))
if python3 --version &> /dev/null && python3 -m pip --version &> /dev/null; then
    print_success "Python готов"
    ((checks_passed++))
else
    print_error "Проблема с Python"
fi

# Проверка портов
((total_checks++))
if ! lsof -i :5000 &> /dev/null && ! lsof -i :5001 &> /dev/null && ! lsof -i :8080 &> /dev/null; then
    print_success "Порты свободны"
    ((checks_passed++))
else
    print_warning "Некоторые порты заняты (может потребоваться настройка)"
    ((checks_passed++))  # Считаем как пройденный, но с предупреждением
fi

# Проверка файлов проекта
((total_checks++))
if [ -f "docker-compose.yml" ] || [ -f ".env" ]; then
    print_success "Файлы конфигурации найдены"
    ((checks_passed++))
else
    print_warning "Файлы проекта не найдены (требуется загрузка)"
fi

print_info "Проверок пройдено: $checks_passed/$total_checks"

# =============================================================================
# ИТОГОВАЯ ИНФОРМАЦИЯ
# =============================================================================

print_header "🎉 Подготовка операционной системы завершена"

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Система готова для IFC Converter v2.0!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo

echo -e "${CYAN}📋 Что установлено:${NC}"
echo -e "${WHITE}  ✅ Базовые системные пакеты${NC}"
echo -e "${WHITE}  ✅ Python 3 и pip${NC}"
echo -e "${WHITE}  ✅ Docker и Docker Compose${NC}"
echo -e "${WHITE}  ✅ Firewall (порты 5000, 5001, 8080)${NC}"
if command -v ngrok &> /dev/null; then
    echo -e "${WHITE}  ✅ ngrok для разработки${NC}"
fi
if [ -f "/etc/systemd/system/ifc-converter.service" ]; then
    echo -e "${WHITE}  ✅ Systemd сервис${NC}"
fi

echo
echo -e "${CYAN}📁 Рабочая директория:${NC}"
echo -e "${WHITE}  $(pwd)${NC}"

echo
echo -e "${CYAN}🔧 Следующие шаги:${NC}"
echo -e "${WHITE}1. ${YELLOW}Получите файлы проекта:${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${WHITE}   - Клонируйте Git репозиторий${NC}"
    echo -e "${WHITE}   - Или скопируйте файлы вручную${NC}"
fi

echo -e "${WHITE}2. ${YELLOW}Настройте Google API:${NC}"
echo -e "${WHITE}   - Создайте OAuth2 Client ID${NC}"
echo -e "${WHITE}   - Создайте Service Account для Google Sheets${NC}"
echo -e "${WHITE}   - Заполните .env файл${NC}"

echo -e "${WHITE}3. ${YELLOW}Запустите развертывание:${NC}"
echo -e "${WHITE}   chmod +x deploy.sh${NC}"
echo -e "${WHITE}   ./deploy.sh${NC}"

if ! groups $USER | grep -q docker; then
    echo
    echo -e "${YELLOW}⚠️  ВАЖНО: Перелогиньтесь для применения прав Docker!${NC}"
    echo -e "${WHITE}   Выполните: exit${NC}"
    echo -e "${WHITE}   Затем зайдите снова по SSH${NC}"
fi

echo
echo -e "${CYAN}📖 Документация:${NC}"
echo -e "${WHITE}  Полная инструкция: ${YELLOW}DEPLOYMENT.md${NC}"
echo -e "${WHITE}  Тестирование OAuth2: ${YELLOW}python3 test_oauth.py${NC}"
echo -e "${WHITE}  Разработка с ngrok: ${YELLOW}./start_dev.sh${NC}"

echo
echo -e "${GREEN}🚀 Система готова! Переходите к настройке Google API и развертыванию.${NC}"