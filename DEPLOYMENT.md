# 🚀 Полная инструкция по развертыванию IFC Converter

## Шаг 1: Подготовка сервера

### Минимальные требования:
- Ubuntu 20.04+ / CentOS 8+ / Debian 10+
- 2GB RAM
- 10GB свободного места
- Доступ root или sudo

### Подготовка Ubuntu/Debian:
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y git curl wget nano ufw

# Настройка firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### Подготовка CentOS/RHEL:
```bash
# Обновление системы
sudo yum update -y

# Установка необходимых пакетов
sudo yum install -y git curl wget nano firewalld

# Настройка firewall
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Шаг 2: Загрузка проекта

```bash
# Перейдите в домашнюю директорию
cd ~

# Клонируйте проект
git clone <your-repository-url> ifc-converter
cd ifc-converter

# Или скопируйте файлы вручную
mkdir ifc-converter
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

### 3.3 Создание сервисного аккаунта

1. Перейдите в "IAM & Admin" > "Service Accounts"
2. Нажмите "Create Service Account"
3. Заполните:
   - **Name**: `ifc-converter-service`
   - **Description**: `Service account for IFC Converter`
4. Нажмите "Create and Continue"
5. Назначьте роли:
   - **Editor** (для доступа к Drive)
6. Нажмите "Continue" и "Done"

### 3.4 Создание ключа

1. Найдите созданный сервисный аккаунт в списке
2. Нажмите на него
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create New Key"
5. Выберите тип **JSON** и нажмите "Create"
6. Сохраните скачанный JSON файл

### 3.5 Создание Google Sheets таблицы

1. Откройте [Google Sheets](https://sheets.google.com/)
2. Создайте новую таблицу
3. Назовите ее, например: "IFC Models Database"
4. Скопируйте **Spreadsheet ID** из URL:
   ```
   https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                      Это ваш Spreadsheet ID
   ```

### 3.6 Предоставление доступа

1. В созданной таблице нажмите кнопку "Поделиться" (Share)
2. Добавьте email сервисного аккаунта (из JSON файла, поле `client_email`)
3. Назначьте права **Редактор** (Editor)
4. Снимите галочку "Notify people" и нажмите "Share"

## Шаг 4: Настройка переменных окружения

Создайте файл `.env`:

```bash
nano .env
```

Заполните его данными из JSON ключа:

```env
# Google Sheets API credentials
GS_TYPE=service_account
GS_PROJECT_ID=your-project-id-from-json
GS_PRIVATE_KEY_ID=your-private-key-id-from-json
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE_FROM_JSON\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GS_CLIENT_ID=your-client-id-from-json
GS_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GS_TOKEN_URI=https://oauth2.googleapis.com/token
GS_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GS_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com

# ID существующей Google Sheets таблицы
GS_SPREADSHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

**⚠️ Важно:** 
- Замените все значения `your-*` на реальные данные из JSON файла
- В `GS_PRIVATE_KEY` сохраните переносы строк как `\n`
- `GS_SPREADSHEET_ID` - это ID вашей Google Sheets таблицы

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
docker-compose build
docker-compose up -d
```

## Шаг 6: Проверка работоспособности

```bash
# Проверка статуса контейнеров
docker-compose ps

# Проверка логов
docker-compose logs -f ifc-converter

# Проверка health check
curl http://localhost:5000/health

# Проверка веб-интерфейса
curl -I http://localhost:5000/
```

## Шаг 7: Настройка SSL (опционально)

### Для домена с Let's Encrypt:

```bash
# Замените на ваш домен
chmod +x setup-ssl.sh
./setup-ssl.sh your-domain.com admin@your-domain.com
```

### Для самоподписанного сертификата:

```bash
# Создание самоподписанного сертификата
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/CN=localhost"

# Обновите nginx.conf для включения HTTPS
# Раскомментируйте соответствующие секции
```

## Шаг 8: Настройка мониторинга

### Логи приложения:
```bash
# Просмотр логов в реальном времени
docker-compose logs -f

# Файловые логи
tail -f logs/app.log

# Логи конкретного сервиса
docker-compose logs -f ifc-converter
```

### Проверка состояния:
```bash
# Health check
curl http://your-domain.com/health

# Статус контейнеров
docker-compose ps
```

## 🔧 Устранение проблем

### Проблема: Контейнер не запускается
```bash
# Проверьте логи
docker-compose logs ifc-converter

# Проверьте конфигурацию
docker-compose config

# Пересоберите образ
docker-compose build --no-cache
```

### Проблема: Google Sheets не работает
```bash
# Проверьте переменные окружения
docker-compose exec ifc-converter env | grep GS_

# Проверьте логи на ошибки API
docker-compose logs ifc-converter | grep -i google
```

### Проблема: Файлы не загружаются
```bash
# Проверьте права доступа к папкам
ls -la uploads downloads

# Проверьте размер диска
df -h

# Увеличьте лимит в nginx.conf если нужно
```

## 📊 Мониторинг и обслуживание

### Автоматические задачи:
```bash
# Очистка старых файлов (добавьте в crontab)
echo "0 2 * * * find /home/user/ifc-converter/downloads -mtime +7 -delete" | crontab -

# Перезапуск раз в неделю (для профилактики)
echo "0 3 * * 0 cd /home/user/ifc-converter && docker-compose restart" | crontab -

# Обновление SSL сертификатов (если используется Let's Encrypt)
echo "0 12 * * * /usr/bin/certbot renew --quiet && cd /home/user/ifc-converter && docker-compose restart nginx" | crontab -
```

## 🎯 Готово!

После выполнения всех шагов ваш IFC Converter будет доступен:

- **HTTP**: http://your-server-ip/ или http://your-domain.com/
- **HTTPS**: https://your-domain.com/ (если настроен SSL)

## 📞 Поддержка

Если возникли проблемы, проверьте:
1. Логи приложения: `docker-compose logs -f`
2. Статус сервисов: `docker-compose ps`
3. Health check: `curl http://localhost:5000/health`
4. Права доступа к Google Sheets
5. Корректность .env файла

# Остановить системные веб-серверы
sudo systemctl stop apache2 || true
sudo systemctl stop nginx || true

# Остановить все Docker контейнеры
docker stop $(docker ps -q) || true
docker-compose down

# Рекомендуется начать без nginx:

Замените docker-compose.yml версией без nginx (первый артефакт)
Запустите: docker-compose up -d
Приложение будет доступно на http://your-server-ip:5000

# После успешного запуска основного приложения можете добавить nginx:

Если нужен nginx, используйте версию с альтернативными портами (второй артефакт)
Доступ будет: http://your-server-ip:8080 и https://your-server-ip:8443