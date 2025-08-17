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


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Главная страница с формой загрузки"""
    return render_template('index.html')


@app.route('/uploads', methods=['POST'])
def upload_file():
    """API для загрузки и обработки IFC-файла"""
    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    # Проверка выбора файла
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Проверка расширения файла
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    try:
        # Генерация уникального имени файла
        file_id = uuid.uuid4().hex
        original_name = file.filename
        file_ext = original_name.rsplit('.', 1)[1].lower()
        filename = f"{file_id}.{file_ext}"
        ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Сохранение файла
        file.save(ifc_path)
        logger.info(f"File uploaded: {original_name} -> {filename}")

        # Обработка IFC
        csv_path = export_flats(ifc_path, app.config['DOWNLOAD_FOLDER'])
        logger.info(f"CSV generated: {csv_path}")

        # Загрузка в Google Sheets
        sheet_url = upload_to_google_sheets(csv_path, original_name)
        logger.info(f"Uploaded to Google Sheets: {sheet_url}")

        # Удаление временных файлов (раскомментировать для продакшена)
        # os.remove(ifc_path)
        # os.remove(csv_path)

        return jsonify({
            "status": "success",
            "sheet_url": sheet_url,
            "csv_path": csv_path
        })

    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    """Скачивание CSV-файла"""
    try:
        safe_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(filename))
        if not os.path.exists(safe_path):
            return jsonify({"error": "File not found"}), 404
        return send_file(safe_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    app.run(host='0.0.0.0', port=5000)