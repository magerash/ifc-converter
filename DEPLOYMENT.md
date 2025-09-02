# 🚀 Развертывание IFC Converter v1.1

Полная инструкция по развертыванию на Ubuntu/Debian с OAuth2 авторизацией и полным функционалом.

## 🏗️ Архитектура v1.1

### Единый сервер с полным функционалом:
- **Flask App (порт 5000)**: Полная функциональность включая OAuth2
- **Nginx (порт 8080/443)**: Reverse proxy для продакшена (опционально)

### Возможности:
- ✅ OAuth2 авторизация через Google
- ✅ Личная история конвертаций (SQLite)
- ✅ Dashboard с детальной аналитикой
- ✅ Базовая конвертация без авторизации
- ✅ Улучшенная система именования файлов с числовой индексацией
- ✅ Расширенный Health Check с HTML интерфейсом
- ✅ Автоматические скрипты установки и настройки

## 1. Подготовка сервера

### 1.1 Автоматическая подготовка
```bash
# Скачайте и запустите подготовку ОС
wget https://raw.githubusercontent.com/your-repo/ifc-converter/main/setup-os.sh
chmod +x setup-os.sh
./setup-os.sh
```

### 1.2 Ручная подготовка
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых пакетов
sudo apt install -y git curl wget nano ufw

# Открытие портов
sudo ufw allow 5000,8080,443/tcp
sudo ufw --force enable
```

## 2. Скачивание проекта

```bash
# Переход в домашнюю директорию
cd ~

# Клонирование проекта
git clone <your-repository-url> ifc-converter
cd ifc-converter
```

## 3. Настройка Google API

### 3.1 Google Cloud Console
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите необходимые APIs:
   - Google Sheets API
   - Google Drive API

### 3.2 OAuth2 Client ID (для авторизации пользователей)
1. APIs & Services → Credentials
2. Create Credentials → OAuth 2.0 Client ID
3. Application Type: **Web application**
4. Authorized redirect URIs: 
   - `http://your-server-ip:5000/auth/callback`
   - `https://your-domain.com/auth/callback` (для продакшена)
5. Сохраните Client ID и Client Secret

### 3.3 Service Account (для Google Sheets API)
1. IAM & Admin → Service Accounts
2. Create Service Account
3. Role: **Editor**
4. Create JSON key и скачайте файл

### 3.4 Google Sheets
1. Создайте новую таблицу в [Google Sheets](https://sheets.google.com/)
2. Поделитесь таблицей с email сервисного аккаунта (права: **Редактор**)
3. Скопируйте Spreadsheet ID из URL таблицы

## 4. Настройка .env файла

Создайте файл `.env`:

```bash
nano .env
```

Заполните данными из Google API:

```env
# Flask
SECRET_KEY=your-super-secret-key-here

# OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Google Sheets API (из JSON ключа сервисного аккаунта)
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

# Database (для второго сервера, если будет использоваться)
DB_PATH=users_history.db

# NGROK (для development)
# NGROK_AUTH_TOKEN=your-ngrok-token
```

⚠️ **Важно**: Замените все `your-*` значения на реальные данные из Google Cloud Console!

## 5. Развертывание

### 5.1 Продакшен (Docker)
```bash
# Дать права на выполнение
chmod +x deploy.sh

# Запустить автоматическое развертывание
./deploy.sh
```

### 5.2 Development с ngrok
```bash
# Установить ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Добавить в .env ваш ngrok token
echo "NGROK_AUTH_TOKEN=your-token" >> .env

# Запустить development с ngrok
chmod +x start_dev.sh
./start_dev.sh
```

При использовании ngrok:
- Автоматически получает публичный URL
- Обновляет .env файл с NGROK_URL
- Показывает URL для настройки в Google Console

### 5.3 Ручное развертывание
```bash
# Остановка старых контейнеров
docker-compose down 2>/dev/null || true

# Сборка и запуск
docker-compose build --no-cache
docker-compose up -d
```

## 6. Проверка развертывания

### 6.1 Статус сервисов
```bash
# Статус контейнеров
docker-compose ps

# Должен показать:
# ifc-converter  Up  0.0.0.0:5000->5000/tcp
# nginx          Up  0.0.0.0:8080->80/tcp (если используется)
```

### 6.2 Health Check
```bash
# Проверка основного сервера
curl http://localhost:5000/health

# Через Nginx (если настроен)  
curl http://localhost:8080/health

# JSON формат
curl http://localhost:5000/health?format=json
```

### 6.3 Проверка OAuth2
```bash
# Диагностический скрипт
python3 google_API_check.py

# Быстрая проверка переменных
docker-compose exec ifc-converter env | grep GOOGLE
```

## 7. Доступ к приложению

После успешного развертывания:

### Локальный доступ:
- **Основной сервер**: http://server-ip:5000/
- **Через Nginx**: http://server-ip:8080/ (если настроен)

### С доменным именем:
- **HTTP**: http://your-domain.com:8080/
- **HTTPS**: https://your-domain.com/ (при настройке SSL)

### Функциональность:

#### Для неавторизованных пользователей:
- ✅ Загрузка и конвертация IFC файлов
- ✅ Скачивание CSV результатов
- ✅ Автоматическая загрузка в Google Sheets
- ❌ История конвертаций не сохраняется

#### Для авторизованных пользователей:
- ✅ Все функции базовой конвертации
- ✅ Безопасный вход через Google OAuth2
- ✅ Личная история всех конвертаций
- ✅ Dashboard с детальной аналитикой
- ✅ Статистика обработанных проектов

## 8. Управление

### 8.1 Команды Docker
```bash
# Просмотр логов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f ifc-converter

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Пересборка
docker-compose build --no-cache
docker-compose up -d
```

### 8.2 Логи приложения
```bash
# Логи в реальном времени
docker-compose logs -f ifc-converter

# Последние 50 строк
docker-compose logs --tail=50 ifc-converter

# Фильтрация ошибок
docker-compose logs ifc-converter | grep ERROR
```

## 9. SSL/HTTPS настройка

### 9.1 Let's Encrypt (автоматически)
```bash
# Автоматическая настройка SSL
./setup-ssl.sh your-domain.com admin@your-domain.com
```

### 9.2 Собственные сертификаты
```bash
# Создать папку для сертификатов
mkdir ssl

# Поместить ваши сертификаты
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem

# Раскомментировать HTTPS секцию в nginx.conf
nano nginx.conf
```

## 10. Мониторинг и обслуживание

### 10.1 Health Check мониторинг
```bash
# HTML интерфейс мониторинга
curl http://localhost:5000/health

# JSON API для автоматических проверок
curl http://localhost:5000/health?format=json
```

### 10.2 База данных пользователей
```bash
# Проверка БД
docker-compose exec ifc-converter ls -la users_history.db

# Статистика
docker-compose exec ifc-converter sqlite3 users_history.db "
SELECT 
  COUNT(*) as total_users,
  (SELECT COUNT(*) FROM conversions) as total_conversions
FROM users;"
```

### 10.3 Автоматическое обслуживание
```bash
# Добавить в crontab для автоматической очистки
crontab -e

# Очистка старых файлов (ежедневно в 2:00)
0 2 * * * find /path/to/ifc-converter/downloads -mtime +7 -delete

# Резервное копирование БД (еженедельно)
0 3 * * 0 cd /path/to/ifc-converter && docker-compose exec -T ifc-converter sqlite3 users_history.db ".backup /app/logs/backup_$(date +\%Y\%m\%d).db"
```

## 🔧 Устранение проблем

### Контейнер не запускается
```bash
# Диагностика
docker-compose ps
docker-compose logs ifc-converter

# Проверка портов
sudo lsof -i :5000

# Полная перезагрузка
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

### OAuth2 не работает
```bash
# Проверка переменных окружения
docker-compose exec ifc-converter env | grep GOOGLE

# Полная диагностика OAuth2
python3 google_API_check.py

# Проверка в Google Console:
# 1. Redirect URIs правильные?
# 2. OAuth2 API включен?
# 3. Client ID и Secret правильные?
```

### Google Sheets API ошибки
```bash
# Проверка Service Account
docker-compose exec ifc-converter env | grep GS_

# Тест подключения
docker-compose exec ifc-converter python3 -c "
from gsheets import validate_gs_credentials
try:
    validate_gs_credentials()
    print('✅ Google Sheets API: OK')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### База данных не создается
```bash
# Пересоздание БД
docker-compose exec ifc-converter python3 -c "
from auth_system import AuthManager
from main import app
with app.app_context():
    auth = AuthManager(app)
    print('✅ Database recreated')
"

# Проверка структуры БД
docker-compose exec ifc-converter sqlite3 users_history.db ".schema"
```

## 📊 Тестирование функциональности

### Тест конвертации (curl)
```bash
# Загрузка IFC файла
curl -X POST -F "file=@model.ifc" http://localhost:5000/uploads

# Скачивание результата
curl -O http://localhost:5000/downloads/model.csv
```

### Тест OAuth2
1. Откройте http://localhost:5000/
2. Нажмите "Войти через Google"
3. Авторизуйтесь
4. Проверьте доступ к Dashboard

### Тест Google Sheets
1. Загрузите IFC файл через веб-интерфейс
2. Проверьте создание новой вкладки в Google Sheets
3. Убедитесь, что данные корректно загружены

## ⚡ Производительность

### Текущие возможности:
- **Файлы**: до 100MB
- **Одновременные пользователи**: ~50
- **Конвертация**: ~2-15 секунд на файл
- **Хранение**: неограниченно (зависит от диска)

### Оптимизация:
```bash
# Мониторинг ресурсов
docker stats

# Увеличение ресурсов контейнера
# Отредактировать docker-compose.yml:
# services:
#   ifc-converter:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
#         reservations:
#           memory: 1G
```

## ✅ Проверочный список

После завершения развертывания убедитесь:

- [ ] Контейнер запущен: `docker-compose ps`
- [ ] Health check работает: `curl http://localhost:5000/health`
- [ ] OAuth2 настроен: переменные GOOGLE_* установлены
- [ ] Google Sheets API работает: `python3 google_API_check.py`
- [ ] База данных создана: `ls users_history.db`
- [ ] Порты открыты: `sudo ufw status`
- [ ] Логи без критических ошибок: `docker-compose logs`

## 🎯 Готово!

После успешного развертывания:
- Приложение работает на порту 5000
- OAuth2 авторизация через Google
- Автоматическая загрузка в Google Sheets
- История конвертаций для авторизованных пользователей
- Расширенный мониторинг через /health

**Используйте IFC Converter v1.1 для профессиональной конвертации BIM файлов!**

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs -f`
2. Запустите диагностику: `python3 google_API_check.py`
3. Проверьте документацию: README.md
4. Создайте issue в GitHub репозитории