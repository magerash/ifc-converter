#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask приложение для обработки IFC-файлов и экспорта в Google Sheets
"""

import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from export_flats import export_flats
from gsheets import upload_to_google_sheets

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['ALLOWED_EXTENSIONS'] = {'ifc', 'ifczip'}

# Настройка логирования
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ifc-exporter')

if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = logging.FileHandler('logs/app.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(file_handler)


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Главная страница с формой загрузки"""
    return render_template('uploads.html')


@app.route('/uploads', methods=['POST'])
def upload_file():
    """API для загрузки и обработки IFC-файла"""
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

        # Сохраняем файл с оригинальным именем
        original_name = file.filename

        # Очищаем имя файла от недопустимых символов для файловой системы
        import re
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', original_name)

        # Если файл с таким именем уже существует, добавляем timestamp
        ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        if os.path.exists(ifc_path):
            name_part = os.path.splitext(safe_filename)[0]
            ext_part = os.path.splitext(safe_filename)[1]
            timestamp = uuid.uuid4().hex[:8]  # Короткий уникальный суффикс
            safe_filename = f"{name_part}_{timestamp}{ext_part}"
            ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

        # Сохранение файла
        file.save(ifc_path)
        logger.info(f"File uploaded: {original_name} -> {safe_filename}")

        # Обработка IFC
        csv_path = export_flats(ifc_path, app.config['DOWNLOAD_FOLDER'], original_name)
        logger.info(f"CSV generated: {csv_path}")

        # Попытка загрузки в Google Sheets
        sheet_url = None
        gs_error_message = None

        try:
            sheet_url = upload_to_google_sheets(csv_path, original_name)
            logger.info(f"Uploaded to Google Sheets: {sheet_url}")
        except Exception as gs_error:
            gs_error_message = str(gs_error)
            logger.warning(f"Google Sheets upload failed: {gs_error_message}")
            # Не прерываем выполнение, просто логируем ошибку

        # Очистка - удаление загруженного IFC файла (опционально)
        # try:
        #     os.remove(ifc_path)
        #     logger.info(f"Temporary file removed: {ifc_path}")
        # except Exception:
        #     pass

        # Формируем ответ с дополнительной информацией
        response_data = {
            "status": "success",
            "csv_path": os.path.basename(csv_path),
            "original_filename": original_name
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
        logger.error(f"Processing error: {str(e)}", exc_info=True)
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


if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    logger.info("Starting IFC to Google Sheets converter...")
    app.run(host='0.0.0.0', port=5000, debug=True)