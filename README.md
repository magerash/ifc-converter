# IFC to CSV Converter - Docker Deployment

Веб-приложение для конвертации IFC файлов в CSV и автоматической загрузки в Google Sheets.

## 🚀 Быстрый запуск

1. **Клонируйте проект на сервер:**
   ```bash
   git clone <your-repo-url>
   cd ifc-converter
   ```

2. **Создайте файл .env с настройками Google API:**
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **Запустите развертывание:**
   ```bash
   chmod +x deployment.sh
   ./deployment.sh
   ```

## 📋 Настройка Google API

1. **Создайте проект в Google Cloud Console:**
   - Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
   - Создайте новый проект или выберите существующий

2. **Включите необходимые API:**
   - Google Sheets API
   - Google Drive API

3. **Создайте сервисный аккаунт:**
   - Перейдите в "IAM & Admin" > "Service Accounts"
   - Создайте новый сервисный аккаунт
   - Скачайте JSON ключ

4. **Заполните .env файл данными из JSON ключа:**
   ```env
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
   GS_SPREADSHEET_ID=your-existing-spreadsheet-id
   ```

5. **Настройте доступ к Google Sheets:**
   - Откройте вашу Google Sheets таблицу
   - Нажмите "Поделиться"
   - Добавьте email сервисного аккаунта с правами "Редактор"

## 🛠 Структура проекта

```
ifc-converter/
├── Dockerfile              # Конфигурация Docker образа
├── docker-compose.yml      # Оркестрация сервисов
├── deploy.sh              # Скрипт автоматического развертывания
├── nginx.conf             # Конфигурация Nginx
├── requirements.txt       # Python зависимости
├── main.py               # Основное Flask приложение
├── export_flats.py       # Логика обработки IFC файлов
├── gsheets.py           # Интеграция с Google Sheets
├── .env                 # Переменные окружения (создать самостоятельно)
├── uploads/             # Папка для загруженных файлов
├── downloads/           # Папка для готовых CSV файлов
└── logs/               # Логи приложения
```

## 🐳 Docker команды

```bash
# Сборка образа
docker-compose build

# Запуск сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down

# Перезапуск
docker-compose restart

# Обновление образа
docker-compose build --no-cache
```

## 🌐 Доступ к приложению

После успешного запуска приложение будет доступно:
- **Напрямую:** http://localhost:5000/
- **Через Nginx:** http://localhost/ (если включен)

## 📊 Мониторинг

- **Health check:** http://localhost:5000/health
- **Логи приложения:** `docker-compose logs ifc-converter`
- **Файловые логи:** `./logs/app.log`

## 🔒 Безопасность

### Для production развертывания:

1. **Настройте HTTPS:**
   - Получите SSL сертификат
   - Разместите файлы в папку `./ssl/`
   - Раскомментируйте HTTPS секцию в `nginx.conf`

2. **Настройте firewall:**
   ```bash
   ufw allow 80
   ufw allow 443
   ufw deny 5000  # Закрываем прямой доступ к Flask
   ```

3. **Обновите домен в nginx.conf:**
   ```nginx
   server_name your-domain.com;
   ```

## 🔧 Настройка переменных окружения

Основные переменные в `.env`:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `GS_SPREADSHEET_ID` | ID Google Sheets таблицы | `1AbCdEfGhIjKlMnOpQrStUv...` |
| `GS_CLIENT_EMAIL` | Email сервисного аккаунта | `service@project.iam.gserviceaccount.com` |
| `GS_PRIVATE_KEY` | Приватный ключ | `-----BEGIN PRIVATE KEY-----\n...` |

## 🚨 Устранение проблем

### Приложение не запускается:
```bash
# Проверьте логи
docker-compose logs ifc-converter

# Проверьте .env файл
cat .env
```

### Google Sheets не работает:
- Убедитесь что все переменные в `.env` заполнены
- Проверьте права доступа сервисного аккаунта к таблице
- Проверьте правильность `GS_SPREADSHEET_ID`

### Большие файлы не загружаются:
- Увеличьте `client_max_body_size` в nginx.conf
- Увеличьте `MAX_CONTENT_LENGTH` в

