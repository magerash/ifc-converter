#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask приложение для обработки IFC-файлов с OAuth2 авторизацией
Упрощенная версия на стандартном порту 5000
"""

import os
import logging
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for

# Инициализация приложения
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['ALLOWED_EXTENSIONS'] = {'ifc', 'ifczip'}

# Секретный ключ для сессий
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Время запуска для uptime
START_TIME = datetime.now()

# Настройка логирования - только в консоль для избежания проблем с правами
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()  # Только консольный вывод
    ]
)
logger = logging.getLogger('ifc-exporter')

# Импорт модулей с обработкой ошибок
try:
    from export_flats import export_flats

    logger.info("✅ export_flats module loaded")
except ImportError as e:
    logger.error(f"❌ Failed to import export_flats: {e}")
    export_flats = None

try:
    from gsheets import upload_to_google_sheets

    logger.info("✅ gsheets module loaded")
except ImportError as e:
    logger.error(f"❌ Failed to import gsheets: {e}")
    upload_to_google_sheets = None

try:
    from file_naming_utils import get_next_indexed_filename

    logger.info("✅ file_naming_utils module loaded")
except ImportError as e:
    logger.error(f"❌ Failed to import file_naming_utils: {e}")
    get_next_indexed_filename = None

try:
    from auth_system import AuthManager, setup_auth_routes

    # Инициализация менеджера авторизации
    auth_manager = AuthManager(app)
    setup_auth_routes(app, auth_manager)
    logger.info("✅ OAuth2 system loaded")
except ImportError as e:
    logger.error(f"❌ Failed to import auth_system: {e}")
    auth_manager = None


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Главная страница"""
    # Если запрошен JSON формат
    if request.args.get('format') == 'json':
        return jsonify({
            "api": "IFC Converter",
            "version": "1.1.0",
            "endpoints": {
                "health": "/health",
                "upload": "/uploads",
                "download": "/downloads/<filename>"
            },
            "documentation": "See /health for system status"
        })

    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('uploads.html')


def check_google_sheets_status():
    """Проверка статуса Google Sheets API с подробной диагностикой"""
    try:
        # Проверяем наличие всех необходимых переменных окружения
        required_vars = [
            'GS_SPREADSHEET_ID',
            'GS_CLIENT_EMAIL',
            'GS_PRIVATE_KEY',
            'GS_PROJECT_ID',
            'GS_TYPE'
        ]

        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if not value or (var.startswith('your-') if isinstance(value, str) else False):
                missing_vars.append(var)

        if missing_vars:
            logger.warning(f"Missing Google Sheets variables: {missing_vars}")
            return 'not_configured'

        # Пробуем импортировать и инициализировать gsheets модуль
        try:
            from gsheets import validate_gs_credentials
            validate_gs_credentials()
            logger.info("Google Sheets API credentials validated successfully")
            return 'configured'
        except ImportError as e:
            logger.error(f"Failed to import gsheets module: {e}")
            return 'error'
        except Exception as e:
            logger.error(f"Google Sheets API validation failed: {e}")
            return 'error'

    except Exception as e:
        logger.error(f"Error checking Google Sheets status: {e}")
        return 'error'


def format_uptime(start_time):
    """Форматирует время работы приложения в читаемый формат"""
    uptime = datetime.now() - start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м {seconds}с"
    elif minutes > 0:
        return f"{minutes}м {seconds}с"
    else:
        return f"{seconds}с"

@app.route('/health')
def health_check():
    """Улучшенная проверка состояния приложения"""
    try:
        # Получаем текущее время для Last Check
        current_time = datetime.now()
        timestamp_formatted = current_time.strftime('%d.%m.%Y %H:%M:%S')

        # Проверяем Google Sheets API
        gs_status = check_google_sheets_status()

        # Если запрос с заголовком Accept: application/json, возвращаем JSON
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                "status": "healthy",
                "timestamp": current_time.isoformat(),
                "version": "1.1.0",
                "uptime": format_uptime(START_TIME),
                "google_sheets_status": gs_status,
                "last_check": timestamp_formatted
            })

        # Получаем дополнительную информацию для HTML страницы
        spreadsheet_id = os.getenv('GS_SPREADSHEET_ID', 'НЕ НАСТРОЕН')
        client_email = os.getenv('GS_CLIENT_EMAIL', 'НЕ НАСТРОЕН')

        # Маскируем чувствительные данные для отображения
        if spreadsheet_id and spreadsheet_id != 'НЕ НАСТРОЕН':
            spreadsheet_display = spreadsheet_id[:15] + "..." if len(spreadsheet_id) > 15 else spreadsheet_id
        else:
            spreadsheet_display = spreadsheet_id

        if client_email and client_email != 'НЕ НАСТРОЕН':
            client_email_display = client_email[:30] + "..." if len(client_email) > 30 else client_email
        else:
            client_email_display = client_email

        # Данные для HTML шаблона
        health_data = {
            'status': 'healthy',
            'timestamp_formatted': timestamp_formatted,
            'version': '1.1.0',
            'uptime': format_uptime(START_TIME),
            'google_sheets_status': gs_status,
            'spreadsheet_id': spreadsheet_display,
            'client_email': client_email_display,
            'last_check': timestamp_formatted  # Добавляем last_check явно
        }

        return render_template('health.html', **health_data)

    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")

        # Возвращаем ошибку, но с базовой информацией
        error_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": error_time
            }), 500

        # Для HTML возвращаем упрощенную страницу с ошибкой
        error_data = {
            'status': 'error',
            'timestamp_formatted': error_time,
            'version': '1.1.0',
            'uptime': 'N/A',
            'google_sheets_status': 'error',
            'spreadsheet_id': 'ERROR',
            'client_email': 'ERROR',
            'last_check': error_time,
            'error_message': str(e)
        }

        return render_template('health.html', **error_data), 500


@app.route('/uploads', methods=['POST'])
def upload_file():
    """API для загрузки и обработки IFC-файла"""
    start_time = time.time()

    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Please use .ifc or .ifczip files"}), 400

        # Сохранение файла с уникальным именем
        original_name = file.filename
        if get_next_indexed_filename:
            safe_filename = get_next_indexed_filename(app.config['UPLOAD_FOLDER'], original_name)
        else:
            safe_filename = original_name

        ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(ifc_path)
        file_size = os.path.getsize(ifc_path)

        # Обработка IFC
        if not export_flats:
            return jsonify({"error": "IFC processing module not available"}), 500

        csv_path = export_flats(ifc_path, app.config['DOWNLOAD_FOLDER'], original_name)
        csv_filename = os.path.basename(csv_path)

        # Подсчет обработанных квартир
        processed_flats = 0
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                processed_flats = sum(1 for line in f) - 1
        except Exception:
            pass

        # Загрузка в Google Sheets
        sheet_url = None
        if upload_to_google_sheets:
            try:
                sheet_url = upload_to_google_sheets(csv_path, original_name)
            except Exception as e:
                logger.warning(f"Google Sheets upload failed: {str(e)}")

        processing_time = time.time() - start_time

        # Сохранение в историю (если пользователь авторизован)
        if 'user' in session and auth_manager:
            conversion_data = {
                'original_filename': original_name,
                'csv_filename': csv_filename,
                'sheet_url': sheet_url,
                'file_size': file_size,
                'processed_flats': processed_flats,
                'processing_time': processing_time,
                'status': 'success'
            }
            try:
                auth_manager.save_conversion(session['user']['id'], conversion_data)
            except Exception as e:
                logger.error(f"Failed to save conversion to history: {str(e)}")

        # Ответ
        response_data = {
            "status": "success",
            "csv_path": csv_filename,
            "original_filename": original_name,
            "processed_flats": processed_flats,
            "processing_time": round(processing_time, 2),
            "sheet_url": sheet_url
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route('/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    """Скачивание CSV-файла"""
    try:
        safe_path = os.path.join(app.config['DOWNLOAD_FOLDER'], os.path.basename(filename))

        if not os.path.exists(safe_path):
            return jsonify({"error": "File not found"}), 404

        return send_file(safe_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Простые fallback маршруты если OAuth2 не загружен
@app.route('/login')
def login_fallback():
    """Fallback для входа"""
    return jsonify({"error": "OAuth2 system not available"}), 503


@app.route('/dashboard')
def dashboard_fallback():
    """Fallback для dashboard"""
    return render_template('dashboard.html', user={'name': 'Guest'})


@app.errorhandler(413)
def too_large(e):
    """Обработка превышения размера файла"""
    return jsonify({"error": "File too large. Maximum size is 100MB"}), 413


@app.errorhandler(500)
def internal_error(e):
    """Обработка внутренних ошибок сервера"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500


def create_app():
    """Фабрика приложений для Gunicorn"""
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    logger.info("IFC Converter v1.1 initialized")
    return app


if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Проверяем development режим с ngrok
    ngrok_url = os.getenv('NGROK_URL')
    if ngrok_url:
        logger.info(f"Starting IFC Converter v1.1 in development mode")
        logger.info(f"Ngrok URL: {ngrok_url}")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        logger.info("Starting IFC Converter v1.1 on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)