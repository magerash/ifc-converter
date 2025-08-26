# IFC Converter 2.0 - Полная система конвертации с OAuth2

Профессиональное веб-приложение для конвертации IFC файлов в CSV с автоматической загрузкой в Google Sheets, OAuth2 авторизацией и системой истории пользователей.

## 🆕 Новые возможности v2.0

### 🏗️ Двухсерверная архитектура
- **Сервер 1 (порт 5000)**: Базовая конвертация без авторизации
- **Сервер 2 (порт 5001)**: OAuth2 + история пользователей + полный функционал
- **Nginx (порт 8080/443)**: Reverse proxy для продакшена

### 🔐 OAuth2 авторизация Google
- Безопасный вход через Google аккаунт
- Личная история конвертаций
- Dashboard с детальной аналитикой
- База данных SQLite для хранения пользователей

### 📊 Улучшенная система именования и мониторинга
- **Числовая индексация файлов**: `File.ifc → File_1.csv, File_2.csv`
- **Уникальные имена листов Google Sheets**: `Sheet → Sheet_1, Sheet_2`
- **Расширенный Health Check** с HTML интерфейсом и JSON API
- **Детальное логирование** всех операций

### ⚡ Автоматизация и DevOps
- **Docker Compose** с multi-service архитектурой
- **Автоматические скрипты** установки и настройки
- **Systemd сервис** для автозапуска
- **Cron задачи** для обслуживания

## 🚀 Быстрый старт

### 1. Подготовка сервера
```bash
# Скачайте и запустите подготовку ОС
wget https://raw.githubusercontent.com/your-repo/ifc-converter/main/setup-os.sh
chmod +x setup-os.sh
./setup-os.sh
```

### 2. Клонирование проекта
```bash
git clone https://github.com/your-username/ifc-converter.git
cd ifc-converter
```

### 3. Настройка Google API

#### A. OAuth2 Client ID (для авторизации пользователей)
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Создайте **OAuth 2.0 Client ID**
3. Тип приложения: **Web application**
4. Authorized redirect URIs: `http://your-server:5001/auth/callback`

#### B. Service Account (для Google Sheets API)
1. Создайте **Service Account** в том же проекте
2. Скачайте **JSON ключ**
3. Создайте **Google Sheets таблицу** и поделитесь с email сервисного аккаунта

### 4. Конфигурация окружения
```bash
# Скопируйте и отредактируйте .env
cp .env.example .env
nano .env
```

Заполните критические переменные:
```env
# OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Service Account (из JSON ключа)
GS_PROJECT_ID=your-project-id
GS_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GS_CLIENT_EMAIL=service-account@project.iam.gserviceaccount.com
GS_SPREADSHEET_ID=your-spreadsheet-id

# Security
SECRET_KEY=your-super-secret-key
```

### 5. Развертывание
```bash
# Автоматическое развертывание
chmod +x deploy.sh
./deploy.sh

# Или вручную
docker-compose build --no-cache
docker-compose up -d
```

### 6. Проверка
```bash
# Статус сервисов
docker-compose ps

# Health checks
curl http://localhost:5000/health    # Основной сервер
curl http://localhost:5001/health    # OAuth2 сервер  
curl http://localhost:8080/health    # Через Nginx

# Тест OAuth2
python3 test_oauth.py
```

## 🌐 Доступ к приложению

После развертывания приложение доступно по следующим адресам:

### Локальный доступ:
- **Основной сервер**: http://server-ip:5000/ *(базовая конвертация)*
- **OAuth2 сервер**: http://server-ip:5001/ *(полный функционал)*
- **Nginx proxy**: http://server-ip:8080/ *(рекомендуется для продакшена)*

### С доменным именем:
- **HTTP**: http://your-domain.com:8080/
- **HTTPS**: https://your-domain.com/ *(при настройке SSL)*

### Функциональность по серверам:

| Сервер | Порт | Функции | Рекомендация |
|--------|------|---------|--------------|
| ifc-converter | 5000 | Базовая конвертация без авторизации | Для простых задач |
| ifc-converter2 | 5001 | OAuth2, история, dashboard | Для полноценной работы |
| nginx | 8080/443 | Reverse proxy, SSL, кеширование | Продакшен |

## 👤 Работа с пользователями

### Для неавторизованных пользователей (порт 5000):
- ✅ Загрузка и конвертация IFC файлов
- ✅ Скачивание CSV результатов
- ✅ Автоматическая загрузка в Google Sheets
- ❌ История конвертаций не сохраняется

### Для авторизованных пользователей (порт 5001):
- ✅ Все функции базового сервера
- ✅ Безопасный вход через Google
- ✅ Личная история всех конвертаций
- ✅ Dashboard с детальной аналитикой
- ✅ Статистика обработанных проектов

## 🛠 Структура проекта v2.0

```
ifc-converter/
├── 🐍 Backend Services
│   ├── main.py                    # Основное Flask приложение
│   ├── auth_system.py            # OAuth2 и система пользователей
│   ├── export_flats.py          # Обработчик IFC файлов
│   ├── gsheets.py               # Google Sheets интеграция
│   └── file_naming_utils.py     # Система именования файлов
│
├── 🐳 Docker & DevOps
│   ├── docker-compose.yml       # Multi-service оркестрация
│   ├── Dockerfile              # Образ приложения
│   ├── nginx.conf             # Reverse proxy конфигурация
│   └── requirements.txt       # Python зависимости
│
├── 🚀 Deployment Scripts
│   ├── deploy.sh             # Автоматическое развертывание
│   ├── setup-os.sh          # Подготовка операционной системы
│   ├── start_dev.sh         # Development с ngrok
│   ├── rebuild.sh           # Пересборка контейнеров
│   └── test_oauth.py        # Тестирование OAuth2
│
├── 🎨 Frontend & Templates
│   ├── templates/
│   │   ├── uploads.html     # Главная страница загрузки
│   │   ├── dashboard.html   # Личный кабинет пользователя
│   │   └── health.html      # Система мониторинга
│
├── 💾 Data & Logs
│   ├── uploads/            # Загруженные IFC файлы
│   ├── downloads/         # Готовые CSV файлы
│   ├── logs/             # Логи приложения
│   └── users_history.db  # База пользователей (SQLite)
│
├── 🔒 Security & Config
│   ├── .env              # Переменные окружения (создать самостоятельно)
│   └── ssl/             # SSL сертификаты (опционально)
│
└── 📚 Documentation
    ├── README.md         # Основная документация
    ├── DEPLOYMENT.md     # Детальная инструкция развертывания
    ├── Keywords.rtf      # SEO ключевые слова
    └── Content.rtf       # Контент для продвижения
```

## 🔧 API Endpoints

### Публичные endpoints (все серверы):
- `GET /` - Главная страница
- `GET /health` - Health check (HTML/JSON)
- `POST /uploads` - Загрузка и обработка IFC файлов
- `GET /downloads/<filename>` - Скачивание CSV файлов

### OAuth2 endpoints (только сервер 5001):
- `GET /login` - Вход через Google OAuth2
- `GET /auth/callback` - OAuth2 callback обработчик
- `GET /logout` - Выход из системы

### Для авторизованных пользователей:
- `GET /dashboard` - Личный кабинет
- `GET /api/history` - История конвертаций (JSON)
- `GET /api/stats` - Статистика пользователя (JSON)

## 🧪 Разработка и тестирование

### Локальная разработка с ngrok:
```bash
# Установите ngrok authtoken в .env
echo "NGROK_AUTH_TOKEN=your-token" >> .env

# Запустите development окружение
./start_dev.sh

# Приложение будет доступно через ngrok URL
# для тестирования OAuth2 redirect'ов
```

### Тестирование OAuth2:
```bash
# Полная диагностика OAuth2 настроек
python3 test_oauth.py

# Быстрая проверка
python3 test_oauth.py --quick

# Проверка переменных окружения
docker-compose exec ifc-converter2 env | grep GOOGLE
```

### Работа с логами:
```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f ifc-converter2

# Логи за последние N строк
docker-compose logs --tail=50 ifc-converter2

# Фильтрация логов
docker-compose logs ifc-converter2 | grep ERROR
```

## 🔒 Безопасность в продакшене

### SSL/TLS настройка:
```bash
# Автоматическая настройка Let's Encrypt
./setup-ssl.sh your-domain.com admin@your-domain.com

# Или поместите сертификаты в ssl/
mkdir ssl
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem
```

### Firewall настройка:
```bash
# Ubuntu/Debian
sudo ufw allow 80,443,5000,5001,8080/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port={80,443,5000,5001,8080}/tcp
sudo firewall-cmd --reload
```

### Переменные окружения:
- ✅ Никогда не публикуйте `.env` файл в Git
- ✅ Используйте сложные пароли для `SECRET_KEY`
- ✅ Регулярно ротируйте API ключи Google
- ✅ Ограничивайте права Service Account в Google Cloud

## 📊 Мониторинг и обслуживание

### Health Check endpoints:
```bash
# HTML интерфейс мониторинга
curl http://localhost:8080/health

# JSON API для автоматических проверок
curl http://localhost:8080/health?format=json
```

Пример JSON ответа:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-27T12:34:56.789012",
  "version": "2.0.0",
  "uptime": "2д 4ч 15м",
  "google_sheets_status": "configured"
}
```

### Логирование:
- **Уровни логов**: DEBUG, INFO, WARNING, ERROR
- **Ротация логов**: автоматическая через cron
- **Местоположение**: `logs/app.log` и Docker logs

### Системная статистика:
```bash
# Использование ресурсов
docker stats

# База данных пользователей
docker-compose exec ifc-converter2 sqlite3 users_history.db "
SELECT 
  COUNT(*) as total_users,
  (SELECT COUNT(*) FROM conversions) as total_conversions,
  (SELECT AVG(processing_time_seconds) FROM conversions WHERE status='success') as avg_time
FROM users;"
```

### Автоматическое обслуживание:
```bash
# Создается автоматически при установке через setup-os.sh
# Или добавьте в crontab вручную:

# Очистка старых файлов (ежедневно в 2:00)
0 2 * * * find /path/to/ifc-converter/downloads -mtime +7 -delete

# Резервное копирование БД (еженедельно)
0 3 * * 0 cd /path/to/ifc-converter && docker-compose exec -T ifc-converter2 sqlite3 users_history.db ".backup /app/logs/backup_$(date +\%Y\%m\%d).db"

# Перезапуск для профилактики (еженедельно)
0 4 * * 0 cd /path/to/ifc-converter && docker-compose restart
```

## 🔧 Устранение проблем

### Проблема: Контейнеры не запускаются
```bash
# Диагностика
docker-compose ps
docker-compose logs

# Проверка портов
sudo lsof -i :5000,5001,8080

# Полная перезагрузка
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Проблема: OAuth2 не работает
```bash
# Проверка переменных окружения
docker-compose exec ifc-converter2 env | grep GOOGLE

# Диагностика OAuth2
python3 test_oauth.py

# Проверка Google Console настроек:
# 1. Redirect URIs правильные?
# 2. JavaScript origins добавлены?  
# 3. OAuth2 API включен?
```

### Проблема: Google Sheets API ошибки
```bash
# Проверка Service Account
docker-compose exec ifc-converter2 env | grep GS_

# Тест подключения к Google API
docker-compose exec ifc-converter2 python3 -c "
from gsheets import validate_gs_credentials
try:
    validate_gs_credentials()
    print('✅ Google Sheets API: OK')
except Exception as e:
    print(f'❌ Google Sheets API Error: {e}')
"

# Проверка прав доступа к таблице
# Service Account email должен быть добавлен в Google Sheets с правами "Редактор"
```

### Проблема: База данных пользователей
```bash
# Проверка существования БД
docker-compose exec ifc-converter2 ls -la users_history.db

# Пересоздание БД
docker-compose exec ifc-converter2 python3 -c "
from auth_system import AuthManager
from main import app
auth = AuthManager(app)
print('✅ Database recreated')
"

# Проверка структуры БД
docker-compose exec ifc-converter2 sqlite3 users_history.db ".schema"
```

## 📈 Примеры использования

### API конвертации (curl):
```bash
# Загрузка IFC файла на основной сервер
curl -X POST -F "file=@model.ifc" http://localhost:5000/uploads

# Загрузка на OAuth2 сервер (требует сессию)
curl -X POST -F "file=@model.ifc" \
  -H "Cookie: session=your-session-cookie" \
  http://localhost:5001/uploads

# Скачивание результата
curl -O http://localhost:8080/downloads/model.csv
```

### Пример успешной конвертации:
```json
{
  "status": "success",
  "csv_path": "Building_Complex_1.csv",
  "original_filename": "Building_Complex.ifc",
  "processed_flats": 48,
  "processing_time": 12.34,
  "sheet_url": "https://docs.google.com/spreadsheets/d/1AbC.../edit#gid=123456",
  "google_sheets_status": "success"
}
```

### Пример истории пользователя:
```json
{
  "status": "success",
  "history": [
    {
      "id": 1,
      "original_filename": "Residential_Building.ifc",
      "csv_filename": "Residential_Building.csv",
      "processed_flats": 24,
      "upload_time": "2025-08-27 14:30:15",
      "processing_time_seconds": 8.7,
      "status": "success",
      "sheet_url": "https://docs.google.com/spreadsheets/.../edit#gid=789"
    }
  ]
}
```

## 🎯 Производительность и масштабирование

### Текущие возможности:
- **Файлы**: до 100MB
- **Одновременные пользователи**: ~50 (зависит от сервера)
- **Конвертация**: ~2-15 секунд на файл (зависит от размера)
- **Хранение**: неограниченно (зависит от диска)

### Оптимизация производительности:
```bash
# Увеличение worker'ов Gunicorn
# В Dockerfile измените: --workers 4

# Настройка Nginx кеширования
# Раскомментируйте proxy_cache в nginx.conf

# Мониторинг ресурсов
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Горизонтальное масштабирование:
1. **Load Balancer**: HAProxy/Nginx upstream для нескольких серверов
2. **База данных**: PostgreSQL/MySQL вместо SQLite
3. **File Storage**: S3/MinIO для файлов
4. **Redis**: для сессий и кеширования

## 🌟 Планы развития v3.0

### В разработке:
- [ ] **RESTful API** с OpenAPI спецификацией
- [ ] **WebSocket** для real-time статуса конвертации  
- [ ] **Multi-tenant** архитектура для enterprise
- [ ] **Kubernetes** deployment манифесты
- [ ] **Telegram/Slack** бот интеграция
- [ ] **Advanced Analytics** с графиками и дашбордами

### Планируется:
- [ ] **Mobile App** (React Native)
- [ ] **Desktop App** (Electron)
- [ ] **Plugin для Revit/ArchiCAD** прямая интеграция
- [ ] **AutoCAD DWG** поддержка
- [ ] **IFC 5.0** поддержка новой спецификации

## 🤝 Участие в разработке

### Для разработчиков:
1. **Fork** проекта на GitHub
2. **Создайте feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit изменения**: `git commit -m 'Add amazing feature'`
4. **Push в branch**: `git push origin feature/amazing-feature`
5. **Откройте Pull Request**

### Стандарты кода:
- **Python**: PEP 8, type hints приветствуются
- **JavaScript**: ES6+, современный синтаксис
- **Docker**: multi-stage builds, безопасные образы
- **Git**: conventional commits

### Тестирование:
```bash
# Линтинг Python кода
flake8 *.py

# Тестирование OAuth2
python3 test_oauth.py

# Интеграционные тесты
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📞 Поддержка и сообщество

### Документация:
- **Основная**: README.md (этот файл)
- **Развертывание**: DEPLOYMENT.md (детальные инструкции)
- **API Reference**: /api/docs (Swagger UI) - в разработке
- **Troubleshooting**: GitHub Issues

### Связь:
- **GitHub Issues**: Для багов и feature requests
- **GitHub Discussions**: Для вопросов и обсуждений
- **Email**: your-email@domain.com
- **Telegram**: @your-telegram (неофициально)

### Поддерживаемые системы:
- ✅ **Ubuntu 20.04+** (рекомендуется)
- ✅ **Debian 10+**  
- ✅ **CentOS 8+**
- ✅ **RHEL 8+**
- ✅ **Rocky Linux 8+**
- ⚠️ **Windows** (через WSL2)
- ⚠️ **macOS** (через Docker Desktop)

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT License**.

```
MIT License

Copyright (c) 2025 IFC Converter Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🎉 Заключение

**IFC Converter 2.0** представляет собой полнофункциональное enterprise-ready решение для конвертации IFC файлов с современной архитектурой, системой авторизации и мониторингом.

### 🎯 Ключевые преимущества:
- 🚀 **Готовность к продакшену** из коробки
- 🔐 **Enterprise-grade безопасность** с OAuth2
- 📊 **Детальная аналитика** и мониторинг  
- 🐳 **Современный DevOps** с Docker и автоматизацией
- 📈 **Горизонтальное масштабирование** ready

### 🏁 Начните использование:
```bash
# Одна команда для полного развертывания
curl -fsSL https://raw.githubusercontent.com/your-repo/ifc-converter/main/setup-os.sh | bash
```

**Конвертируйте IFC файлы профессионально с IFC Converter 2.0!**

---

<div align="center">

**Made with ❤️ for BIM professionals**

[⭐ Star нас на GitHub](https://github.com/your-username/ifc-converter) | [🐛 Сообщить о баге](https://github.com/your-username/ifc-converter/issues) | [💬 Обсуждения](https://github.com/your-username/ifc-converter/discussions)

</div>