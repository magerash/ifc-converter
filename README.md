# IFC Converter 2.0 - Полная система конвертации с OAuth2

Веб-приложение для конвертации IFC файлов в CSV с автоматической загрузкой в Google Sheets, OAuth2 авторизацией и историей пользователей.

## 🆕 Новые возможности v2.0

### 🔐 OAuth2 авторизация
- Вход через Google аккаунт
- История конвертаций для каждого пользователя
- Личный кабинет со статистикой
- Безопасное хранение данных

### 📊 Улучшенная система именования
- **Числовая индексация файлов**: File.ifc → File_1.ifc, File_2.ifc
- **Уникальные имена листов Google Sheets**: Sheet → Sheet_1, Sheet_2
- **Защита от дублирования** в uploads, downloads и Google Sheets

### 🔍 Расширенный Health Check
- Красивая HTML страница с информацией о системе
- Мониторинг статуса Google Sheets API
- Время работы системы (uptime)
- API endpoint для автоматических проверок

### 📈 Аналитика и статистика
- Подробная статистика по конвертациям
- Анализ обработанных квартир
- Время обработки файлов
- Отслеживание ошибок

## 🚀 Быстрый запуск

### 1. Клонирование проекта
```bash
git clone <your-repo-url>
cd ifc-converter
```

### 2. Настройка Google API

#### Google OAuth2 (для авторизации пользователей)
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите **Google+ API** (или **Google People API**)
4. Создайте **OAuth 2.0 Client ID**:
   - Application type: **Web application**  
   - Authorized redirect URIs: `http://your-domain.com/auth/callback`
5. Скопируйте **Client ID** и **Client Secret**

#### Google Sheets API (для работы с таблицами)
1. В том же проекте включите:
   - **Google Sheets API**
   - **Google Drive API**
2. Создайте **Service Account**:
   - IAM & Admin → Service Accounts → Create Service Account
   - Роль: **Editor** (для доступа к Drive)
3. Скачайте **JSON ключ** сервисного аккаунта
4. Создайте **Google Sheets таблицу** и поделитесь ею с email сервисного аккаунта

### 3. Настройка переменных окружения
```bash
cp .env.example .env
nano .env
```

Заполните все необходимые переменные:
```env
# OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Google Sheets (из JSON ключа)
GS_PROJECT_ID=your-project-id
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=service-account@project.iam.gserviceaccount.com
GS_SPREADSHEET_ID=your-spreadsheet-id

# Безопасность
SECRET_KEY=your-super-secret-key-for-sessions
```

### 4. Развертывание
```bash
chmod +x deploy.sh
./deploy.sh
```

## 🌐 Доступ к приложению

После запуска приложение доступно:
- **Основное приложение**: http://localhost:5000/
- **Health Check**: http://localhost:5000/health
- **API Health**: http://localhost:5000/health?format=json
- **Через Nginx**: http://localhost:8080/ (если включен)

## 👤 Работа с пользователями

### Авторизованный пользователь
1. **Вход**: Нажмите "Войти через Google"
2. **Dashboard**: Личный кабинет с историей и статистикой
3. **Загрузка файлов**: Прямо из dashboard с автосохранением в истории
4. **История**: Полный список конвертаций с ссылками на результаты

### Неавторизованный пользователь
- Может конвертировать файлы без регистрации
- История не сохраняется
- Доступ ко всем основным функциям

## 🛠 Структура проекта v2.0

```
ifc-converter/
├── main.py                    # Основное приложение Flask
├── auth_system.py            # OAuth2 авторизация и история
├── file_naming_utils.py      # Система именования файлов
├── export_flats.py          # Обработка IFC файлов  
├── gsheets.py               # Интеграция с Google Sheets
├── google_API_check.py      # Диагностика Google API
├── 
├── templates/               # HTML шаблоны
│   ├── uploads.html        # Главная страница
│   ├── dashboard.html      # Личный кабинет
│   └── health.html         # Health check страница
├── 
├── uploads/                # Загруженные IFC файлы
├── downloads/             # Готовые CSV файлы
├── logs/                  # Логи приложения
├── 
├── users_history.db       # База данных пользователей (SQLite)
├── 
├── docker-compose.yml     # Docker оркестрация
├── Dockerfile            # Конфигурация контейнера
├── nginx.conf           # Конфигурация веб-сервера
├── 
├── deploy.sh           # Автоматическое развертывание
├── rebuild.sh         # Пересборка контейнеров
├── setup-os.sh       # Подготовка операционной системы
└── .env              # Переменные окружения (создать самостоятельно)
```

## 🔧 API Endpoints

### Публичные
- `GET /` - Главная страница
- `GET /health` - Health check (HTML/JSON)
- `POST /uploads` - Загрузка и обработка IFC файлов
- `GET /downloads/<filename>` - Скачивание CSV файлов

### Авторизация  
- `GET /login` - Страница входа (OAuth2)
- `GET /auth/callback` - OAuth2 callback
- `GET /logout` - Выход из системы

### Для авторизованных пользователей
- `GET /dashboard` - Личный кабинет
- `GET /api/history` - История конвертаций (JSON)
- `GET /api/stats` - Статистика пользователя (JSON)

## 📊 Примеры API ответов

### Health Check JSON
```json
{
  "status": "healthy",
  "timestamp": "2025-08-24T12:34:56.789012",
  "version": "2.0.0",
  "uptime": "2д 4ч 15м",
  "google_sheets_status": "configured"
}
```

### Успешная конвертация
```json
{
  "status": "success",
  "csv_path": "project_model.csv",
  "original_filename": "project_model.ifc",
  "processed_flats": 48,
  "processing_time": 12.34,
  "sheet_url": "https://docs.google.com/spreadsheets/d/.../edit#gid=123456",
  "google_sheets_status": "success"
}
```

### История пользователя
```json
{
  "status": "success",
  "history": [
    {
      "id": 1,
      "original_filename": "Building_A.ifc",
      "csv_filename": "Building_A.csv", 
      "processed_flats": 24,
      "upload_time": "2025-08-24 12:30:15",
      "status": "success",
      "sheet_url": "https://docs.google.com/spreadsheets/.../edit#gid=123"
    }
  ]
}
```

## 🐳 Docker команды

### Основные команды
```bash
# Полная пересборка
docker-compose build --no-cache

# Запуск сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f ifc-converter

# Остановка всех сервисов
docker-compose down

# Перезапуск определенного сервиса
docker-compose restart ifc-converter

# Просмотр статуса
docker-compose ps
```

### Отладка и обслуживание
```bash
# Подключение к контейнеру
docker-compose exec ifc-converter bash

# Очистка логов
docker-compose logs --tail=0 -f ifc-converter

# Просмотр использования ресурсов
docker stats ifc-converter

# Резервное копирование базы данных
docker-compose exec ifc-converter sqlite3 users_history.db ".backup /app/logs/backup.db"
```

## 🔒 Безопасность в продакшене

### Настройка HTTPS
1. **Получите SSL сертификат** (Let's Encrypt/Cloudflare)
2. **Поместите файлы в папку ssl/**:
   ```
   ssl/
   ├── cert.pem
   └── key.pem
   ```
3. **Раскомментируйте HTTPS секцию** в nginx.conf
4. **Обновите OAuth2 redirect URI** на https://

### Firewall
```bash
# Разрешить HTTP/HTTPS
ufw allow 80
ufw allow 443

# Закрыть прямой доступ к Flask (безопасность)
ufw deny 5000

# Разрешить SSH
ufw allow ssh
ufw enable
```

### Переменные окружения
- ✅ **Никогда не публикуйте .env файл**
- ✅ **Используйте сложные пароли для SECRET_KEY**
- ✅ **Ротируйте ключи API регулярно**
- ✅ **Ограничьте права Service Account в Google Cloud**

## 🔧 Устранение проблем

### Проблема: OAuth2 не работает
```bash
# Проверьте настройки
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET

# Проверьте redirect URI в Google Console:
# Должен быть: http://your-domain.com/auth/callback

# Проверьте, включен ли Google+ API
curl -H "Authorization: Bearer $TOKEN" \
  "https://www.googleapis.com/oauth2/v2/userinfo"
```

### Проблема: База данных не создается
```bash
# Проверьте права доступа
ls -la users_history.db

# Пересоздайте базу данных
docker-compose exec ifc-converter python3 -c "
from auth_system import AuthManager
from main import app
auth = AuthManager(app)
print('Database recreated')
"
```

### Проблема: Google Sheets API не работает
```bash
# Запустите диагностику
docker-compose exec ifc-converter python3 google_API_check.py

# Проверьте переменные окружения
docker-compose exec ifc-converter env | grep GS_

# Проверьте права доступа к таблице
# Service Account email должен иметь роль "Редактор"
```

### Проблема: Файлы дублируются
```bash
# Проверьте систему именования
docker-compose exec ifc-converter python3 -c "
from file_naming_utils import get_next_indexed_filename
print(get_next_indexed_filename('./downloads', 'test.csv'))
"

# Очистите старые файлы (если нужно)
find downloads/ -name "*_[0-9]*" -mtime +7 -delete
```

## 📈 Мониторинг и аналитика

### Логи приложения
```bash
# Логи в реальном времени
docker-compose logs -f

# Только ошибки
docker-compose logs ifc-converter | grep ERROR

# Статистика по конвертациям
docker-compose exec ifc-converter sqlite3 users_history.db "
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successful,
  AVG(processing_time_seconds) as avg_time
FROM conversions;
"
```

### Метрики системы
```bash
# Использование места на диске
docker-compose exec ifc-converter df -h

# Размер базы данных
docker-compose exec ifc-converter ls -lh users_history.db

# Количество файлов
docker-compose exec ifc-converter find uploads/ -type f | wc -l
docker-compose exec ifc-converter find downloads/ -type f | wc -l
```

## 📅 Автоматизация обслуживания

### Crontab задачи
```bash
# Очистка старых файлов (раз в день)
echo "0 2 * * * cd /path/to/ifc-converter && find downloads/ -mtime +7 -delete" | crontab -

# Резервное копирование базы данных (раз в неделю)
echo "0 3 * * 0 cd /path/to/ifc-converter && docker-compose exec -T ifc-converter sqlite3 users_history.db '.backup /app/logs/backup_$(date +\%Y\%m\%d).db'" | crontab -

# Перезапуск для профилактики (раз в неделю)
echo "0 4 * * 0 cd /path/to/ifc-converter && docker-compose restart" | crontab -

# Обновление SSL сертификатов (Let's Encrypt)
echo "0 12 * * * /usr/bin/certbot renew --quiet && cd /path/to/ifc-converter && docker-compose restart nginx" | crontab -
```

### Скрипты обслуживания
```bash
# Создайте maintenance.sh
cat > maintenance.sh << 'EOF'
#!/bin/bash
echo "🧹 Очистка старых файлов..."
find downloads/ -mtime +7 -delete
find uploads/ -mtime +3 -delete

echo "💾 Резервное копирование..."
docker-compose exec -T ifc-converter sqlite3 users_history.db ".backup /app/logs/backup_$(date +%Y%m%d).db"

echo "📊 Статистика использования..."
docker stats --no-stream ifc-converter
docker-compose exec ifc-converter df -h

echo "✅ Обслуживание завершено"
EOF

chmod +x maintenance.sh
```

## 🎯 Итоги обновления v2.0

### ✅ Реализованные улучшения

1. **Числовая индексация файлов**
   - File.ifc → File_1.ifc, File_2.ifc  
   - Работает для uploads, downloads и Google Sheets
   - Защита от конфликтов имен

2. **Улучшенный Health Check**
   - Красивая HTML страница
   - JSON API для автоматических проверок
   - Информация о времени работы и статусе

3. **OAuth2 авторизация Google**
   - Безопасный вход через Google аккаунт
   - История конвертаций для каждого пользователя
   - Личный кабинет с аналитикой
   - База данных SQLite для хранения истории

### 🚀 Готово к использованию

После выполнения всех шагов у вас будет:

- **Полнофункциональный IFC конвертер** с веб-интерфейсом
- **OAuth2 авторизация** через Google
- **История конвертаций** для каждого пользователя  
- **Автоматическая загрузка** в Google Sheets
- **Система мониторинга** и health checks
- **Docker развертывание** с одной командой

### 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи**: `docker-compose logs -f`
2. **Запустите диагностику**: `python3 google_API_check.py`
3. **Проверьте health check**: http://localhost:5000/health
4. **Изучите документацию** Google OAuth2 и Sheets API

---

**IFC Converter 2.0** | Made with ❤️ for BIM professionals

🏗️ **Конвертируйте IFC файлы легко и безопасно!**