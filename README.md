# IFC Converter v1.1 - Конвертация BIM файлов

Современное веб-приложение для конвертации IFC файлов в CSV с автоматической загрузкой в Google Sheets, OAuth2 авторизацией и системой истории пользователей.

![IFC Converter v1.1](https://img.shields.io/badge/Version-1.1-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-green.svg)
![Flask](https://img.shields.io/badge/Flask-2.3-red.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🆕 Новые возможности v1.1

### 🔐 OAuth2 авторизация Google
- Безопасный вход через Google аккаунт
- Личная история всех конвертаций
- Dashboard с детальной аналитикой пользователя
- База данных SQLite для хранения пользователей и истории

### 📊 Улучшенная система именования и мониторинга
- **Числовая индексация файлов**: `File.ifc → File_1.csv, File_2.csv`
- **Уникальные имена листов Google Sheets**: `Sheet → Sheet_1, Sheet_2`
- **Расширенный Health Check** с HTML интерфейсом и JSON API
- **Детальное логирование** всех операций и ошибок

### ⚡ Автоматизация и DevOps
- **Docker** контейнеризация для стабильного развертывания
- **Автоматические скрипты** установки и настройки
- **Nginx** reverse proxy для продакшена (опционально)
- **Диагностические инструменты** для проверки Google API

## 🚀 Быстрый старт

### 1. Клонирование проекта
```bash
git clone https://github.com/your-username/ifc-converter.git
cd ifc-converter
```

### 2. Настройка Google API
Создайте проект в [Google Cloud Console](https://console.cloud.google.com/) и настройте:

#### OAuth2 Client ID:
- Тип приложения: **Web application**  
- Authorized redirect URIs: `http://your-server:5000/auth/callback`

#### Service Account:
- Создайте Service Account с ролью **Editor**
- Скачайте JSON ключ
- Создайте Google Sheets таблицу и поделитесь с Service Account

### 3. Конфигурация окружения
```bash
# Скопируйте и отредактируйте .env
cp .env.example .env
nano .env
```

Минимальная конфигурация:
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

### 4. Развертывание
```bash
# Автоматическое развертывание
chmod +x deploy.sh
./deploy.sh

# Или вручную
docker-compose build --no-cache
docker-compose up -d
```

### 5. Проверка
```bash
# Health check
curl http://localhost:5000/health

# Диагностика Google API
python3 google_API_check.py
```

## 🌐 Доступ к приложению

После развертывания приложение доступно:

- **Основной сервер**: http://server-ip:5000/
- **С Nginx**: http://server-ip:8080/ (при настройке)
- **HTTPS**: https://your-domain.com/ (при настройке SSL)

### Функциональность:

#### 🔓 Без авторизации:
- ✅ Конвертация IFC файлов в CSV
- ✅ Скачивание результатов
- ✅ Автоматическая загрузка в Google Sheets
- ❌ История не сохраняется

#### 🔐 С авторизацией через Google:
- ✅ Все функции базовой конвертации
- ✅ Личная история конвертаций
- ✅ Dashboard с аналитикой
- ✅ Статистика обработанных проектов

## 🛠 Структура проекта v1.1

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
│   ├── docker-compose.yml       # Контейнеризация
│   ├── Dockerfile              # Образ приложения
│   ├── nginx.conf             # Reverse proxy
│   └── requirements.txt       # Python зависимости
│
├── 🚀 Deployment Scripts
│   ├── deploy.sh             # Автоматическое развертывание
│   ├── setup-os.sh          # Подготовка ОС
│   ├── start_dev.sh         # Development с ngrok
│   ├── rebuild.sh           # Пересборка контейнеров
│   └── google_API_check.py  # Диагностика Google API
│
├── 🎨 Frontend & Templates  
│   ├── templates/
│   │   ├── uploads.html     # Главная страница
│   │   ├── dashboard.html   # Личный кабинет
│   │   └── health.html      # Мониторинг системы
│
├── 💾 Data & Logs
│   ├── uploads/            # Загруженные IFC файлы
│   ├── downloads/         # Готовые CSV файлы
│   ├── logs/             # Логи приложения
│   └── users_history.db  # База пользователей (SQLite)
│
├── 🔒 Security & Config
│   ├── .env              # Переменные окружения
│   └── ssl/             # SSL сертификаты (опционально)
│
└── 📚 Documentation
    ├── README.md         # Основная документация (этот файл)
    ├── DEPLOYMENT.md     # Детальная инструкция развертывания
    └── Keywords.rtf      # SEO ключевые слова
```

## 🔧 API Endpoints

### Публичные endpoints:
- `GET /` - Главная страница с конвертером
- `GET /health` - Health check (HTML/JSON)  
- `POST /uploads` - Загрузка и обработка IFC файлов
- `GET /downloads/<filename>` - Скачивание CSV файлов

### OAuth2 endpoints:
- `GET /login` - Вход через Google OAuth2
- `GET /auth/callback` - OAuth2 callback обработчик  
- `GET /logout` - Выход из системы

### Для авторизованных пользователей:
- `GET /dashboard` - Личный кабинет с историей
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

### Тестирование Google API:
```bash
# Полная диагностика
python3 google_API_check.py

# Проверка переменных окружения  
docker-compose exec ifc-converter env | grep GOOGLE
```

### Работа с логами:
```bash
# Логи в реальном времени
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f ifc-converter

# Фильтрация ошибок
docker-compose logs ifc-converter | grep ERROR
```

## 📊 Мониторинг и обслуживание

### Health Check:
```bash
# HTML интерфейс мониторинга
curl http://localhost:5000/health

# JSON API для автоматических проверок
curl http://localhost:5000/health?format=json
```

Пример JSON ответа:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T12:34:56.789012",
  "version": "1.1.0", 
  "uptime": "2д 4ч 15м",
  "google_sheets_status": "configured"
}
```

### Системная статистика:
```bash
# Использование ресурсов
docker stats

# База данных пользователей
docker-compose exec ifc-converter sqlite3 users_history.db "
SELECT 
  COUNT(*) as total_users,
  (SELECT COUNT(*) FROM conversions) as total_conversions,
  (SELECT AVG(processing_time_seconds) FROM conversions WHERE status='success') as avg_time
FROM users;"
```

### Автоматическое обслуживание:
```bash
# Добавьте в crontab для автоматической очистки
crontab -e

# Очистка старых файлов (ежедневно в 2:00)
0 2 * * * find /path/to/ifc-converter/downloads -mtime +7 -delete

# Резервное копирование БД (еженедельно)
0 3 * * 0 cd /path/to/ifc-converter && docker-compose exec -T ifc-converter sqlite3 users_history.db ".backup /app/logs/backup_$(date +\%Y\%m\%d).db"
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
sudo ufw allow 80,443,5000,8080/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port={80,443,5000,8080}/tcp
sudo firewall-cmd --reload
```

### Рекомендации по безопасности:
- ✅ Никогда не публикуйте `.env` файл в Git
- ✅ Используйте сложные пароли для `SECRET_KEY`
- ✅ Регулярно ротируйте API ключи Google
- ✅ Ограничивайте права Service Account в Google Cloud

## 🔧 Устранение проблем

### Контейнер не запускается:
```bash
# Диагностика
docker-compose ps
docker-compose logs

# Полная перезагрузка
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### OAuth2 не работает:
```bash
# Проверка настроек
python3 google_API_check.py

# Убедитесь в Google Console:
# 1. Redirect URIs правильные?
# 2. OAuth2 API включен?
# 3. Client ID и Secret корректные?
```

### Google Sheets API ошибки:
```bash
# Тест подключения
docker-compose exec ifc-converter python3 -c "
from gsheets import validate_gs_credentials
validate_gs_credentials()
print('✅ OK')
"

# Проверьте:
# 1. Service Account email добавлен в Google Sheets?
# 2. Права 'Редактор' предоставлены?
# 3. Google Sheets API включен?
```

## 📈 Примеры использования

### API конвертации (curl):
```bash
# Загрузка IFC файла
curl -X POST -F "file=@model.ifc" http://localhost:5000/uploads

# Скачивание результата
curl -O http://localhost:5000/downloads/model.csv
```

### Пример успешной конвертации:
```json
{
  "status": "success",
  "csv_path": "Building_Complex_1.csv",
  "original_filename": "Building_Complex.ifc",
  "processed_flats": 48,
  "processing_time": 12.34,
  "sheet_url": "https://docs.google.com/spreadsheets/d/1AbC.../edit#gid=123456"
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
      "upload_time": "2025-01-15 14:30:15",
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
# Мониторинг ресурсов
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Увеличение ресурсов в docker-compose.yml
services:
  ifc-converter:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Горизонтальное масштабирование:
1. **Load Balancer**: HAProxy/Nginx upstream для нескольких серверов
2. **База данных**: PostgreSQL/MySQL вместо SQLite
3. **File Storage**: S3/MinIO для файлов  
4. **Redis**: для сессий и кеширования

## 🌟 Roadmap и планы развития

### В разработке v2.0:
- [ ] **RESTful API** с OpenAPI/Swagger документацией
- [ ] **WebSocket** для real-time статуса конвертации
- [ ] **Advanced Analytics** с графиками и дашбордами  
- [ ] **Multi-tenant** архитектура для enterprise
- [ ] **Kubernetes** deployment манифесты

### Планируется v3.0:
- [ ] **Mobile App** (React Native)
- [ ] **Desktop App** (Electron)
- [ ] **Plugin для Revit/ArchiCAD** прямая интеграция
- [ ] **AutoCAD DWG** поддержка
- [ ] **IFC 5.0** поддержка новой спецификации
- [ ] **Telegram/Slack** бот интеграция

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
python3 google_API_check.py

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

## 🏆 Особенности и преимущества

### 🎯 Ключевые преимущества v1.1:
- 🚀 **Enterprise-ready** архитектура из коробки
- 🔐 **Профессиональная безопасность** с OAuth2
- 📊 **Детальная аналитика** и мониторинг
- 🐳 **Современный DevOps** с Docker и автоматизацией
- 📈 **Готовность к масштабированию**

### 🛡️ Безопасность:
- OAuth2 авторизация через Google
- Безопасное хранение API ключей
- SQLite база данных с шифрованием
- HTTPS поддержка из коробки
- Валидация всех входных данных

### ⚡ Производительность:
- Асинхронная обработка файлов
- Эффективные алгоритмы парсинга IFC
- Умное кеширование результатов
- Оптимизированные Docker образы
- Автоматическая очистка временных файлов

### 🔧 Удобство использования:
- Интуитивный веб-интерфейс
- Drag & Drop загрузка файлов
- Real-time прогресс обработки  
- Автоматическая загрузка в Google Sheets
- История всех конвертаций

## 📊 Статистика и метрики

### Поддерживаемые форматы:
- **Входные**: IFC, IFCZIP
- **Выходные**: CSV, XLSX (через Google Sheets)
- **Версии IFC**: IFC 2x3, IFC4

### Извлекаемые данные:
- Типы квартир (1С, 2С, 3С, 4С)
- Площади помещений в м²
- Номера секций и этажей
- Номера квартир
- Метаданные объектов

### Интеграции:
- **Google Sheets API** - автоматическая загрузка
- **Google OAuth2** - безопасная авторизация
- **ifcopenshell** - профессиональный парсер IFC
- **SQLite** - надежное хранение истории

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

**IFC Converter v1.1** представляет собой полнофункциональное enterprise-ready решение для конвертации IFC файлов с современной архитектурой, системой авторизации и профессиональным мониторингом.

### 🏁 Начните использование:
```bash
# Одна команда для полного развертывания  
git clone https://github.com/your-username/ifc-converter.git
cd ifc-converter
chmod +x deploy.sh
./deploy.sh
```

**Конвертируйте IFC файлы профессионально с IFC Converter v1.1!**

---

<div align="center">

**Made with ❤️ for BIM professionals**

[⭐ Star на GitHub](https://github.com/your-username/ifc-converter) | [🐛 Сообщить о баге](https://github.com/your-username/ifc-converter/issues) | [💬 Обсуждения](https://github.com/your-username/ifc-converter/discussions)

**IFC Converter v1.1** - Профессиональная конвертация BIM файлов

</div>