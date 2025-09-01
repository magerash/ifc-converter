# 🚀 Развертывание IFC Converter v2.0

Простая инструкция по развертыванию на Ubuntu/Debian.

## 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых пакетов
sudo apt install -y git curl wget nano

# Открытие порта 5000
sudo ufw allow 5000
```

## 2. Скачивание проекта

```bash
# Перейти в домашнюю директорию
cd ~

# Клонировать проект
git clone <your-repository-url> ifc-converter
cd ifc-converter
```

## 3. Настройка Google API

### 3.1 Google Cloud Console
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте проект
3. Включите APIs:
   - Google Sheets API
   - Google Drive API

### 3.2 OAuth2 Client ID
1. APIs & Services > Credentials
2. Create OAuth 2.0 Client ID
3. Web application
4. Authorized redirect URIs: `http://your-server-ip:5000/auth/callback`
5. Сохраните Client ID и Client Secret

### 3.3 Service Account
1. IAM & Admin > Service Accounts
2. Create Service Account
3. Role: Editor
4. Create JSON key и скачайте

### 3.4 Google Sheets
1. Создайте таблицу в [Google Sheets](https://sheets.google.com/)
2. Поделитесь с email сервисного аккаунта (права: Редактор)
3. Скопируйте Spreadsheet ID из URL

## 4. Настройка .env файла

Создайте файл `.env`:

```bash
nano .env
```

Заполните данными из Google API:

```env
# OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Flask
SECRET_KEY=your-super-secret-key-here

# Google Sheets API (из JSON ключа)
GS_TYPE=service_account
GS_PROJECT_ID=your-project-id
GS_PRIVATE_KEY_ID=your-private-key-id
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=service-account@your-project.iam.gserviceaccount.com
GS_CLIENT_ID=your-client-id
GS_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GS_TOKEN_URI=https://oauth2.googleapis.com/token
GS_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GS_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/service-account%40your-project.iam.gserviceaccount.com
GS_SPREADSHEET_ID=your-spreadsheet-id-here
```

⚠️ **Важно**: Замените все `your-*` значения на реальные данные!

## 5. Развертывание

```bash
# Дать права на выполнение
chmod +x deploy.sh

# Запустить развертывание
./deploy.sh
```

Если нужно перелогиниться после установки Docker, выполните:
```bash
exit
# Зайдите снова по SSH
cd ~/ifc-converter
./deploy.sh
```

## 6. Проверка

После развертывания приложение доступно по адресу:
- http://your-server-ip:5000/

Проверить состояние:
```bash
# Статус контейнера
docker-compose ps

# Логи приложения
docker-compose logs -f

# Health check
curl http://localhost:5000/health
```

## 7. Управление

```bash
# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Пересборка
docker-compose build --no-cache
docker-compose up -d
```

## 🔧 Решение проблем

### Контейнер не запускается
```bash
# Проверить логи
docker-compose logs

# Проверить порт
sudo lsof -i :5000
```

### OAuth2 не работает
1. Проверьте переменные в .env
2. Убедитесь что redirect URI правильный в Google Console
3. Проверьте, что OAuth2 API включен

### Google Sheets не работает
1. Проверьте Service Account email в .env
2. Убедитесь что таблица расшарена с сервисным аккаунтом
3. Проверьте права "Редактор" для сервисного аккаунта

## ✅ Готово!

После успешного развертывания:
- Приложение работает на порту 5000
- OAuth2 авторизация через Google
- Автоматическая загрузка в Google Sheets
- История конвертаций для авторизованных пользователей