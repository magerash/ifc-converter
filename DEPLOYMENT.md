# 🚀 Полная инструкция по развертыванию IFC Converter v2.0

## Обновления в версии 2.0

### 🔄 Двухсерверная конфигурация
- **Сервер 1**: порт 5000 (основной)
- **Сервер 2**: порт 5001 (дополнительный, с OAuth2)
- **Nginx**: порт 8080 (проксирует на сервер 2)

### ✨ Новые возможности
- OAuth2 авторизация через Google
- История конвертаций пользователей
- Числовая индексация файлов
- Расширенный Health Check

## Шаг 1: Подготовка сервера

### Минимальные требования:
- Ubuntu 20.04+ / CentOS 8+ / Debian 10+
- 2GB RAM (рекомендуется 4GB для двух серверов)
- 20GB свободного места
- Доступ root или sudo

### Подготовка Ubuntu/Debian:
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y git curl wget nano ufw python3-pip

# Настройка firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 5000   # Основной сервер
sudo ufw allow 5001   # OAuth2 сервер
sudo ufw allow 8080   # Nginx proxy
sudo ufw allow 80
sudo ufw allow 443
```

### Подготовка CentOS/RHEL:
```bash
# Обновление системы
sudo yum update -y

# Установка необходимых пакетов
sudo yum install -y git curl wget nano firewalld python3-pip

# Настройка firewall
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Шаг 2: Загрузка проекта

```bash
# Перейдите в домашнюю директорию
cd ~

# Клонируйте проект (замените на ваш URL)
git clone https://github.com/your-username/ifc-converter.git ifc-converter
cd ifc-converter

# Или скопируйте файлы вручную
mkdir -p ifc-converter
cd ifc-converter
# Скопируйте все файлы проекта
```

## Шаг 3: Настройка Google API

### 3.1 Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Запишите **Project ID**

### 3.2 Включение API

1. В меню слева выберите "APIs & Services" > "Library"
2. Найдите и включите:
   - **Google Sheets API**
   - **Google Drive API** 
   - **Google OAuth2 API** (для авторизации пользователей)

### 3.3 Создание OAuth2 Client ID

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "OAuth client ID"
3. Выберите "Web application"
4. Заполните:
   - **Name**: `IFC Converter OAuth2`
   - **Authorized JavaScript origins**:
     - `http://your-server-ip:5001`
     - `http://your-domain.com:8080`
     - `https://your-domain.com`
   - **Authorized redirect URIs**:
     - `http://your-server-ip:5001/auth/callback`
     - `http://your-domain.com:8080/auth/callback`
     - `https://your-domain.com/auth/callback`
5. Сохраните **Client ID** и **Client Secret**

### 3.4 Создание сервисного аккаунта

1. Перейдите в "IAM & Admin" > "Service Accounts"
2. Нажмите "Create Service Account"
3. Заполните:
   - **Name**: `ifc-converter-service`
   - **Description**: `Service account for IFC Converter Sheets API`
4. Назначьте роли:
   - **Editor** (для доступа к Drive)
5. Создайте и скачайте **JSON ключ**

### 3.5 Создание Google Sheets таблицы

1. Откройте [Google Sheets](https://sheets.google.com/)
2. Создайте новую таблицу: "IFC Models Database"
3. Скопируйте **Spreadsheet ID** из URL
4. Поделитесь таблицей с email сервисного аккаунта (роль: Редактор)

## Шаг 4: Настройка переменных окружения

Создайте файл `.env`:

```bash
nano .env
```

Заполните его:

```env
# OAuth2 Configuration
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-oauth-client-secret

# Flask Configuration
SECRET_KEY=your-super-secret-key-for-sessions-$(openssl rand -hex 32)
FLASK_ENV=production
FLASK_DEBUG=0

# Google Sheets API (из JSON ключа сервисного аккаунта)
GS_TYPE=service_account
GS_PROJECT_ID=your-project-id-from-json
GS_PRIVATE_KEY_ID=your-private-key-id-from-json
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE_FROM_JSON\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=service-account@your-project.iam.gserviceaccount.com
GS_CLIENT_ID=your-client-id-from-json
GS_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GS_TOKEN_URI=https://oauth2.googleapis.com/token
GS_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GS_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/service-account%40your-project.iam.gserviceaccount.com

# ID существующей Google Sheets таблицы
GS_SPREADSHEET_ID=your-spreadsheet-id-from-step-3-5

# Database path for second server
DB_PATH=users_history.db

# Ngrok URL (для разработки)
NGROK_URL=
```

**⚠️ Важные замены:**
- Все `your-*` значения замените на реальные данные
- `GS_PRIVATE_KEY` должен содержать `\n` вместо реальных переносов строк
- `SECRET_KEY` должен быть уникальным и сложным

## Шаг 5: Развертывание

### Автоматическое развертывание:

```bash
# Дайте права на выполнение
chmod +x deploy.sh

# Запустите развертывание
./deploy.sh
```

### Ручное развертывание:

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Перелогинитесь для применения прав Docker
exit
# Зайдите снова по SSH

# Создание директорий
mkdir -p uploads downloads logs ssl

# Запуск сервисов
docker-compose build --no-cache
docker-compose up -d
```

## Шаг 6: Проверка работоспособности

```bash
# Проверка статуса контейнеров
docker-compose ps

# Должно показать:
# ifc-converter   - порт 5000 (основной)
# ifc-converter2  - порт 5001 (OAuth2)
# nginx          - порт 8080 (прокси)

# Проверка логов
docker-compose logs -f ifc-converter
docker-compose logs -f ifc-converter2

# Проверка health check
curl http://localhost:5000/health    # Основной сервер
curl http://localhost:5001/health    # OAuth2 сервер
curl http://localhost:8080/health    # Через Nginx

# Проверка веб-интерфейса
curl -I http://localhost:5000/       # Основной функционал
curl -I http://localhost:5001/       # OAuth2 функционал
curl -I http://localhost:8080/       # Публичный доступ
```

## Шаг 7: Тестирование OAuth2

### Использование тестового скрипта:

```bash
# Активируйте виртуальное окружение (если используете)
source venv/bin/activate

# Установите зависимости для тестирования
pip install colorama requests python-dotenv

# Запустите тест OAuth2
python3 test_oauth.py

# Или быстрый тест
python3 test_oauth.py --quick
```

### Ручное тестирование:

1. **Откройте в браузере**: `http://your-server-ip:5001/`
2. **Нажмите "Войти через Google"**
3. **Авторизуйтесь** и проверьте редирект
4. **Проверьте dashboard**: `http://your-server-ip:5001/dashboard`

## Шаг 8: Настройка доменного имени (опционально)

### Если у вас есть домен:

```bash
# Обновите DNS записи:
# A запись: your-domain.com -> IP вашего сервера

# Обновите .env файл
nano .env
```

Добавьте в `.env`:
```env
DOMAIN_NAME=your-domain.com
```

Обновите OAuth2 настройки в Google Console:
- Authorized origins: `https://your-domain.com`
- Redirect URIs: `https://your-domain.com/auth/callback`

## Шаг 9: Настройка SSL (Let's Encrypt)

### Автоматическая настройка SSL:

```bash
# Создайте скрипт setup-ssl.sh
cat > setup-ssl.sh << 'EOF'
#!/bin/bash
DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Usage: $0 your-domain.com admin@your-domain.com"
    exit 1
fi

# Установка Certbot
sudo apt update
sudo apt install -y certbot

# Получение сертификата
sudo certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos --no-eff-email

# Копирование сертификатов
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
sudo chown -R $USER:$USER ssl/

# Обновление nginx.conf
sed -i 's/# server {/server {/g' nginx.conf
sed -i 's/# listen 443/listen 443/g' nginx.conf
sed -i 's/# }/}/g' nginx.conf

echo "SSL настроен для $DOMAIN"
echo "Перезапустите контейнеры: docker-compose restart"
EOF

chmod +x setup-ssl.sh

# Запустите настройку SSL
./setup-ssl.sh your-domain.com admin@your-domain.com
```

### Ручная настройка SSL:

```bash
# Поместите ваши SSL сертификаты в папку ssl/
mkdir -p ssl
# Скопируйте:
# ssl/cert.pem - сертификат
# ssl/key.pem  - приватный ключ

# Раскомментируйте HTTPS секцию в nginx.conf
nano nginx.conf

# Перезапустите nginx
docker-compose restart nginx
```

## Шаг 10: Доступ к приложению

После завершения настройки ваше приложение доступно:

### Локальный доступ:
- **Основной сервер**: http://server-ip:5000/
- **OAuth2 сервер**: http://server-ip:5001/ 
- **Через Nginx**: http://server-ip:8080/

### Доменный доступ:
- **HTTP**: http://your-domain.com:8080/
- **HTTPS**: https://your-domain.com/ (если настроен SSL)

### Функциональность по серверам:
- **Порт 5000**: Базовая конвертация без авторизации
- **Порт 5001**: Полный функционал с OAuth2 и историей
- **Порт 8080/443**: Публичный доступ (рекомендуется)

## 🔧 Устранение проблем

### Проблема: Контейнеры не запускаются

```bash
# Проверьте логи
docker-compose logs

# Освободите порты, если заняты
sudo lsof -i :5000
sudo lsof -i :5001
sudo lsof -i :8080

# Остановите системные сервисы если нужно
sudo systemctl stop apache2 nginx || true

# Пересоберите контейнеры
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Проблема: OAuth2 не работает

```bash
# Проверьте переменные окружения
docker-compose exec ifc-converter2 env | grep GOOGLE

# Проверьте .env файл
cat .env | grep GOOGLE

# Запустите диагностику
docker-compose exec ifc-converter2 python3 test_oauth.py

# Проверьте настройки в Google Console:
# 1. Redirect URIs корректные?
# 2. JavaScript origins добавлены?
# 3. API включены?
```

### Проблема: База данных не создается

```bash
# Проверьте права доступа
docker-compose exec ifc-converter2 ls -la users_history.db

# Пересоздайте базу данных
docker-compose exec ifc-converter2 python3 -c "
from auth_system import AuthManager
from main import app
auth = AuthManager(app)
print('Database recreated')
"
```

### Проблема: Google Sheets API не работает

```bash
# Проверьте сервисный аккаунт
docker-compose exec ifc-converter2 env | grep GS_

# Проверьте права доступа к таблице
# Email сервисного аккаунта должен иметь права "Редактор"

# Тест Google API подключения
docker-compose exec ifc-converter2 python3 -c "
import os
from gsheets import validate_gs_credentials
try:
    validate_gs_credentials()
    print('Google Sheets API: OK')
except Exception as e:
    print(f'Google Sheets API Error: {e}')
"
```

## 📊 Мониторинг и обслуживание

### Логи приложений:
```bash
# Основной сервер (порт 5000)
docker-compose logs -f ifc-converter

# OAuth2 сервер (порт 5001)  
docker-compose logs -f ifc-converter2

# Nginx
docker-compose logs -f nginx

# Все сервисы
docker-compose logs -f
```

### Статистика системы:
```bash
# Использование ресурсов
docker stats

# Дисковое пространство
df -h

# База данных пользователей
docker-compose exec ifc-converter2 sqlite3 users_history.db "
SELECT 
  COUNT(*) as total_users,
  (SELECT COUNT(*) FROM conversions) as total_conversions,
  (SELECT COUNT(*) FROM conversions WHERE status='success') as successful_conversions
FROM users;
"
```

### Автоматическое обслуживание:
```bash
# Создайте crontab задачи
crontab -e

# Добавьте:
# Очистка старых файлов (ежедневно в 2:00)
0 2 * * * cd /path/to/ifc-converter && find downloads/ -mtime +7 -delete && find uploads/ -mtime +3 -delete

# Резервное копирование базы данных (еженедельно)
0 3 * * 0 cd /path/to/ifc-converter && docker-compose exec -T ifc-converter2 sqlite3 users_history.db ".backup /app/logs/backup_$(date +\%Y\%m\%d).db"

# Перезапуск для профилактики (еженедельно)
0 4 * * 0 cd /path/to/ifc-converter && docker-compose restart

# Обновление SSL (если используется Let's Encrypt)
0 12 * * * /usr/bin/certbot renew --quiet && cd /path/to/ifc-converter && docker-compose restart nginx
```

## 🎯 Итоги развертывания v2.0

### ✅ Что получилось:

1. **Двухсерверная архитектура**
   - Сервер 1 (5000): Базовая конвертация
   - Сервер 2 (5001): OAuth2 + история пользователей
   - Nginx (8080/443): Публичный доступ

2. **OAuth2 авторизация**
   - Безопасный вход через Google
   - История конвертаций для каждого пользователя
   - Личный кабинет с аналитикой

3. **Улучшенное именование файлов**
   - Числовая индексация (File_1.csv, File_2.csv)
   - Защита от конфликтов имен

4. **Расширенный мониторинг**
   - Health check с подробной информацией
   - Логирование и аналитика

### 🚀 Готово к использованию:

После выполнения всех шагов у вас есть полнофункциональный IFC Converter с:
- Веб-интерфейсом на порту 8080 (рекомендуется)
- OAuth2 авторизацией через Google
- Автоматической загрузкой в Google Sheets
- Историей конвертаций для пользователей
- SSL поддержкой для продакшена

### 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Запустите тесты: `python3 test_oauth.py`
3. Проверьте health check: http://your-server:8080/health
4. Изучите конфигурацию: `docker-compose config`

---

**IFC Converter 2.0** | Профессиональная конвертация IFC файлов с OAuth2

🏗️ **Конвертируйте, авторизуйтесь, отслеживайте историю!**