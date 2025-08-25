#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask приложение для обработки IFC-файлов с OAuth2 авторизацией и историей
Версия без автосоздания шаблонов - шаблоны хранятся в папке templates/
"""

import os
import logging
import sys
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
from export_flats import export_flats
from gsheets import upload_to_google_sheets
from file_naming_utils import get_next_indexed_filename
from auth_system import AuthManager, setup_auth_routes

# Инициализация приложения
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['ALLOWED_EXTENSIONS'] = {'ifc', 'ifczip'}

# Секретный ключ для сессий (в продакшене должен быть в переменных окружения)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# OAuth2 конфигурация
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Время запуска приложения для uptime
START_TIME = datetime.now()

# Настройка логирования
log_level = logging.DEBUG if os.getenv('FLASK_DEBUG', '0') == '1' else logging.INFO

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('ifc-exporter')

# Инициализация менеджера авторизации
auth_manager = AuthManager(app)

# Настройка маршрутов авторизации
setup_auth_routes(app, auth_manager)


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def format_uptime(start_time):
    """Форматирование времени работы приложения"""
    uptime = datetime.now() - start_time
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м"
    else:
        return f"{minutes}м {seconds}с"


def check_google_sheets_status():
    """Проверка статуса Google Sheets API"""
    try:
        required_vars = ['GS_SPREADSHEET_ID', 'GS_CLIENT_EMAIL', 'GS_PRIVATE_KEY']
        if all(os.getenv(var) for var in required_vars):
            return 'configured'
        else:
            return 'not_configured'
    except Exception:
        return 'error'


@app.route('/')
def index():
    """Главная страница"""
    # Если пользователь авторизован, перенаправляем в dashboard
    if 'user' in session:
        return redirect(url_for('dashboard'))

    # Показываем обычную страницу загрузки для неавторизованных пользователей
    return render_template('uploads.html')


@app.route('/health')
# @app.route('/health')
# def health_check():
#     # Временно закомментируйте текущий код и верните простой тест
#     return "TEST: Health check works"  # Это поможет проверить работу роута
def health_check():
    try:
        """Улучшенная проверка состояния приложения"""
        # Если запрос с заголовком Accept: application/json, возвращаем JSON
        if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "uptime": format_uptime(START_TIME),
                "google_sheets_status": check_google_sheets_status()
            })

        # Иначе возвращаем HTML страницу
        health_data = {
            'status': 'healthy',
            'timestamp_formatted': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'version': '2.0.0',
            'uptime': format_uptime(START_TIME),
            'google_sheets_status': check_google_sheets_status(),
            'spreadsheet_id': os.getenv('GS_SPREADSHEET_ID', 'НЕ НАСТРОЕН')
        }

        return render_template('health.html', **health_data)

    except Exception as e:
        logger.error(f"Error rendering health template: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/uploads', methods=['POST'])
def upload_file():
    """API для загрузки и обработки IFC-файла с сохранением в историю"""
    start_time = time.time()

    try:
        # Проверка наличия файла в запросе
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        # Проверка выбора файла
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Проверка расширения файла
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Please use .ifc or .ifczip files"}), 400

        # Получение уникального имени файла с числовой индексацией
        original_name = file.filename
        safe_filename = get_next_indexed_filename(app.config['UPLOAD_FOLDER'], original_name)
        ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

        # Сохранение файла
        file.save(ifc_path)
        file_size = os.path.getsize(ifc_path)
        logger.info(f"File uploaded: {original_name} -> {safe_filename} ({file_size} bytes)")

        # Обработка IFC
        csv_path = export_flats(ifc_path, app.config['DOWNLOAD_FOLDER'], original_name)
        csv_filename = os.path.basename(csv_path)
        logger.info(f"CSV generated: {csv_path}")

        # Подсчет количества обработанных квартир
        processed_flats = 0
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                processed_flats = sum(1 for line in f) - 1  # Исключаем заголовок
        except Exception:
            pass

        # Попытка загрузки в Google Sheets
        sheet_url = None
        gs_error_message = None

        try:
            sheet_url = upload_to_google_sheets(csv_path, original_name)
            logger.info(f"Uploaded to Google Sheets: {sheet_url}")
        except Exception as gs_error:
            gs_error_message = str(gs_error)
            logger.warning(f"Google Sheets upload failed: {gs_error_message}")

        processing_time = time.time() - start_time

        # Сохранение в историю (если пользователь авторизован)
        if 'user' in session:
            conversion_data = {
                'original_filename': original_name,
                'csv_filename': csv_filename,
                'sheet_url': sheet_url,
                'file_size': file_size,
                'processed_flats': processed_flats,
                'processing_time': processing_time,
                'status': 'success',
                'error_message': gs_error_message
            }

            try:
                auth_manager.save_conversion(session['user']['id'], conversion_data)
                logger.info(f"Conversion saved to history for user: {session['user']['email']}")
            except Exception as e:
                logger.error(f"Failed to save conversion to history: {str(e)}")

        # Формируем ответ
        response_data = {
            "status": "success",
            "csv_path": csv_filename,
            "original_filename": original_name,
            "processed_flats": processed_flats,
            "processing_time": round(processing_time, 2)
        }

        # Добавляем информацию о Google Sheets
        if sheet_url:
            response_data["sheet_url"] = sheet_url
            response_data["google_sheets_status"] = "success"
        else:
            response_data["sheet_url"] = None
            response_data["google_sheets_status"] = "failed"
            response_data["google_sheets_error"] = gs_error_message

        return jsonify(response_data)

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Processing error: {str(e)}", exc_info=True)

        # Сохранение ошибки в историю (если пользователь авторизован)
        if 'user' in session:
            error_conversion_data = {
                'original_filename': request.files['file'].filename if 'file' in request.files else 'unknown',
                'csv_filename': None,
                'sheet_url': None,
                'file_size': 0,
                'processed_flats': 0,
                'processing_time': processing_time,
                'status': 'error',
                'error_message': str(e)
            }

            try:
                auth_manager.save_conversion(session['user']['id'], error_conversion_data)
            except Exception:
                pass

        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route('/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    """Скачивание CSV-файла"""
    try:
        safe_path = os.path.join(app.config['DOWNLOAD_FOLDER'], os.path.basename(filename))

        if not os.path.exists(safe_path):
            logger.warning(f"File not found: {safe_path}")
            return jsonify({"error": "File not found"}), 404

        return send_file(safe_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"error": str(e)}), 500


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

    # Проверяем наличие templates директории
    if not os.path.exists('templates'):
        logger.error("Templates directory not found! Please create templates/ folder with HTML files.")
        raise FileNotFoundError("Templates directory is missing")

    # Проверяем наличие обязательных шаблонов
    required_templates = ['uploads.html', 'health.html', 'dashboard.html']
    missing_templates = []

    for template in required_templates:
        template_path = os.path.join('templates', template)
        if not os.path.exists(template_path):
            missing_templates.append(template)

    if missing_templates:
        logger.error(f"Missing template files: {missing_templates}")
        raise FileNotFoundError(f"Missing template files: {missing_templates}")

    logger.info("IFC to Google Sheets converter with OAuth2 initialized")
    logger.info(f"Templates directory: {os.path.abspath('templates')}")
    return app


if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Проверяем наличие шаблонов
    if not os.path.exists('templates'):
        logger.error("Templates directory not found!")
        logger.error("Please create templates/ directory with required HTML files:")
        logger.error("  - templates/uploads.html")
        logger.error("  - templates/health.html")
        logger.error("  - templates/dashboard.html")
        sys.exit(1)

    # Проверяем наличие обязательных шаблонов
    required_templates = ['uploads.html', 'health.html', 'dashboard.html']
    missing_templates = []

    for template in required_templates:
        template_path = os.path.join('templates', template)
        if not os.path.exists(template_path):
            missing_templates.append(template)

    if missing_templates:
        logger.error(f"Missing template files: {missing_templates}")
        logger.error("Please create the missing template files in templates/ directory")
        sys.exit(1)

    # Запуск в режиме разработки
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    logger.info("Starting IFC to Google Sheets converter with OAuth2 in development mode...")
    # app.run(host='0.0.0.0', port=5000, debug=debug_mode)
    # Определяем порт через переменную окружения
    port = int(os.getenv('PORT', 5000))                   # ======================= ВТОРОЙ СЕРВЕР ======================= #
    app.run(host='0.0.0.0', port=port, debug=debug_mode)  # ======================= ВТОРОЙ СЕРВЕР ======================= #