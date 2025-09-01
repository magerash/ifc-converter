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

# Секретный ключ для сессий
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# OAuth2 конфигурация
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Время запуска для uptime
START_TIME = datetime.now()

# Настройка логирования
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
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


@app.route('/')
def index():
    """Главная страница"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('uploads.html')


@app.route('/health')
def health_check():
    """Проверка состояния приложения"""
    uptime = datetime.now() - START_TIME

    if request.args.get('format') == 'json':
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "uptime": str(uptime)
        })

    return render_template('health.html',
                           status='healthy',
                           version='2.0.0',
                           uptime=str(uptime))


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
        safe_filename = get_next_indexed_filename(app.config['UPLOAD_FOLDER'], original_name)
        ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

        file.save(ifc_path)
        file_size = os.path.getsize(ifc_path)

        # Обработка IFC
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
        try:
            sheet_url = upload_to_google_sheets(csv_path, original_name)
        except Exception as e:
            logger.warning(f"Google Sheets upload failed: {str(e)}")

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


@app.errorhandler(413)
def too_large(e):
    """Обработка превышения размера файла"""
    return jsonify({"error": "File too large. Maximum size is 100MB"}), 413


@app.errorhandler(500)
def internal_error(e):
    """Обработка внутренних ошибок сервера"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Проверяем development режим с ngrok
    ngrok_url = os.getenv('NGROK_URL')
    if ngrok_url:
        logger.info(f"Starting IFC Converter v2.0 in development mode")
        logger.info(f"Ngrok URL: {ngrok_url}")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        logger.info("Starting IFC Converter v2.0 on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)