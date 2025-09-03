#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask приложение для обработки IFC-файлов с поддержкой множественной загрузки
Версия 1.2 с объединением данных из нескольких файлов и OAuth2
"""

import os
import logging
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for
from apartment_analytics import ApartmentAnalyzer, process_and_visualize

# Инициализация приложения
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB на файл
app.config['ALLOWED_EXTENSIONS'] = {'ifc', 'ifczip'}
app.config['MAX_FILES'] = 10  # Максимум файлов за раз

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
    from export_flats import export_flats, export_flats_multiple, DEFAULT_AREA_COEFFICIENT

    logger.info("✅ export_flats module loaded")
except ImportError as e:
    logger.error(f"❌ Failed to import export_flats: {e}")
    export_flats = None
    export_flats_multiple = None
    DEFAULT_AREA_COEFFICIENT = 0.9

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


@app.route('/')
def index():
    """Главная страница"""
    # Если запрошен JSON формат
    if request.args.get('format') == 'json':
        return jsonify({
            "api": "IFC Converter",
            "version": "1.2.0",
            "endpoints": {
                "health": "/health",
                "upload": "/uploads",
                "download": "/downloads/<filename>"
            },
            "features": {
                "multiple_files": True,
                "area_coefficient": True,
                "oauth2": auth_manager is not None
            },
            "documentation": "See /health for system status"
        })

    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('uploads.html')


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
                "version": "1.2.0",
                "uptime": format_uptime(START_TIME),
                "google_sheets_status": gs_status,
                "last_check": timestamp_formatted,
                "features": {
                    "multiple_files_upload": True,
                    "area_coefficient": True,
                    "oauth2_enabled": auth_manager is not None
                }
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
            'version': '1.2.0',
            'uptime': format_uptime(START_TIME),
            'google_sheets_status': gs_status,
            'spreadsheet_id': spreadsheet_display,
            'client_email': client_email_display,
            'last_check': timestamp_formatted
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
            'version': '1.2.0',
            'uptime': 'N/A',
            'google_sheets_status': 'error',
            'spreadsheet_id': 'ERROR',
            'client_email': 'ERROR',
            'last_check': error_time,
            'error_message': str(e)
        }

        return render_template('health.html', **error_data), 500


@app.route('/uploads', methods=['POST'])
def upload_files():
    """API для загрузки и обработки нескольких IFC-файлов (обратная совместимость с одиночной загрузкой)"""
    start_time = time.time()

    try:
        # Проверка наличия файлов в запросе
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        # Поддержка как одиночной загрузки (для обратной совместимости), так и множественной
        files = request.files.getlist('files') if 'files' in request.files else []

        # Если использовался старый API с одним файлом
        if not files and 'file' in request.files:
            single_file = request.files['file']
            if single_file.filename:
                files = [single_file]

        if not files or all(f.filename == '' for f in files):
            return jsonify({"error": "No selected files"}), 400

        # Проверка количества файлов
        if len(files) > app.config['MAX_FILES']:
            return jsonify({"error": f"Too many files. Maximum is {app.config['MAX_FILES']}"}), 400

        # Получение коэффициента площади из запроса
        area_coefficient = DEFAULT_AREA_COEFFICIENT
        try:
            area_coefficient = float(request.form.get('area_coefficient', DEFAULT_AREA_COEFFICIENT))
            # Валидация коэффициента
            if not 0.5 <= area_coefficient <= 1.0:
                area_coefficient = DEFAULT_AREA_COEFFICIENT
                logger.warning(f"Invalid area coefficient, using default: {DEFAULT_AREA_COEFFICIENT}")
        except (ValueError, TypeError):
            area_coefficient = DEFAULT_AREA_COEFFICIENT

        # Список для хранения путей загруженных файлов
        uploaded_paths = []
        original_names = []
        total_size = 0

        # Сохраняем все файлы
        for file in files:
            if not allowed_file(file.filename):
                logger.warning(f"Skipping invalid file type: {file.filename}")
                continue

            original_name = file.filename
            if get_next_indexed_filename:
                safe_filename = get_next_indexed_filename(app.config['UPLOAD_FOLDER'], original_name)
            else:
                safe_filename = original_name

            ifc_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            file.save(ifc_path)
            file_size = os.path.getsize(ifc_path)
            total_size += file_size

            uploaded_paths.append(ifc_path)
            original_names.append(original_name)

            logger.info(f"File uploaded: {original_name} -> {safe_filename} ({file_size} bytes)")

        if not uploaded_paths:
            return jsonify({"error": "No valid IFC files were uploaded"}), 400

        # Проверка наличия модуля обработки
        if not export_flats_multiple and not export_flats:
            return jsonify({"error": "IFC processing module not available"}), 500

        # Определяем имя для объединенного файла
        if len(uploaded_paths) == 1:
            combined_name = os.path.splitext(original_names[0])[0]
        else:
            combined_name = f"combined_{len(uploaded_paths)}_files"

        # Обработка IFC файлов
        if export_flats_multiple and len(uploaded_paths) > 1:
            # Используем новую функцию для множественной обработки
            csv_path = export_flats_multiple(
                uploaded_paths,
                app.config['DOWNLOAD_FOLDER'],
                area_coefficient,
                combined_name
            )
        elif export_flats:
            # Fallback к старой функции для одного файла
            csv_path = export_flats(
                uploaded_paths[0],
                app.config['DOWNLOAD_FOLDER'],
                original_names[0]
            )
        else:
            return jsonify({"error": "IFC processing module not available"}), 500

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

        if upload_to_google_sheets:
            try:
                sheet_url = upload_to_google_sheets(csv_path, combined_name)
                logger.info(f"Uploaded to Google Sheets: {sheet_url}")
            except Exception as gs_error:
                gs_error_message = str(gs_error)
                logger.warning(f"Google Sheets upload failed: {gs_error_message}")

        processing_time = time.time() - start_time

        # Сохранение в историю (если пользователь авторизован)
        if 'user' in session and auth_manager:
            conversion_data = {
                'original_filename': ', '.join(original_names),
                'csv_filename': csv_filename,
                'sheet_url': sheet_url,
                'file_size': total_size,
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
            "original_filename": original_names[0] if len(original_names) == 1 else None,  # Для обратной совместимости
            "original_filenames": original_names,
            "files_processed": len(uploaded_paths),
            "processed_flats": processed_flats,
            "processing_time": round(processing_time, 2),
            "area_coefficient": area_coefficient,
            "combined": len(uploaded_paths) > 1
        }

        # Добавляем информацию о Google Sheets
        if sheet_url:
            response_data["sheet_url"] = sheet_url
            response_data["google_sheets_status"] = "success"
        else:
            response_data["sheet_url"] = None
            response_data["google_sheets_status"] = "failed"
            if gs_error_message:
                response_data["google_sheets_error"] = gs_error_message

        return jsonify(response_data)

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Processing error: {str(e)}", exc_info=True)

        # Сохранение ошибки в историю
        if 'user' in session and auth_manager:
            error_conversion_data = {
                'original_filename': 'multiple files' if 'files' in request.files else 'unknown',
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


# Простые fallback маршруты если OAuth2 не загружен
@app.route('/login')
def login_fallback():
    """Fallback для входа"""
    if auth_manager:
        # Если auth_manager загружен, перенаправляем на правильный маршрут
        return redirect(url_for('login'))
    return jsonify({"error": "OAuth2 system not available"}), 503


@app.route('/dashboard')
def dashboard_fallback():
    """Fallback для dashboard"""
    if auth_manager and 'user' in session:
        # Если пользователь авторизован, показываем полноценный dashboard
        user_id = session['user']['id']
        stats = auth_manager.get_user_stats(user_id)
        history = auth_manager.get_user_history(user_id, limit=20)

        return render_template('dashboard.html',
                               user=session['user'],
                               stats=stats,
                               history=history)
    # Если не авторизован - показываем гостевой dashboard
    return render_template('dashboard.html',
                           user={'name': 'Guest', 'email': 'guest@example.com'},
                           stats={'total_conversions': 0, 'total_flats_processed': 0, 'recent_conversions': 0},
                           history=[])

@app.route('/api/visualize/<filename>', methods=['GET'])
def visualize_apartments(filename):
    """API для генерации гистограммы распределения квартир"""
    try:
        # Путь к CSV файлу
        csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return jsonify({"error": "CSV file not found", "filename": filename}), 404

        logger.info(f"Generating visualization for: {filename}")

        # Импортируем модуль аналитики
        try:
            from apartment_analytics import process_and_visualize
        except ImportError as e:
            logger.error(f"Failed to import apartment_analytics: {e}")
            return jsonify({"error": "Analytics module not available"}), 500

        # Генерация визуализации
        img_base64 = process_and_visualize(csv_path)

        if img_base64:
            logger.info(f"Visualization generated successfully for {filename}")
            return jsonify({
                "status": "success",
                "image": img_base64,
                "filename": filename
            })
        else:
            logger.error(f"Failed to generate visualization for {filename}")
            return jsonify({"error": "Failed to generate visualization"}), 500

    except Exception as e:
        logger.error(f"Visualization error for {filename}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics/<filename>', methods=['GET'])
def get_analytics(filename):
    """API для получения аналитики по квартирам"""
    try:
        csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found for analytics: {csv_path}")
            return jsonify({"error": "CSV file not found", "filename": filename}), 404

        logger.info(f"Generating analytics for: {filename}")

        # Импортируем модуль аналитики
        try:
            from apartment_analytics import ApartmentAnalyzer
        except ImportError as e:
            logger.error(f"Failed to import ApartmentAnalyzer: {e}")
            return jsonify({"error": "Analytics module not available"}), 500

        # Создание анализатора и подготовка данных
        analyzer = ApartmentAnalyzer()
        df = analyzer.prepare_histogram_data(csv_path)

        if df is None:
            logger.error(f"Failed to prepare data for analytics: {filename}")
            return jsonify({"error": "Failed to prepare data"}), 500

        # Генерация отчета
        report = analyzer.generate_analytics_report(df)

        logger.info(f"Analytics generated successfully for {filename}")
        return jsonify({
            "status": "success",
            "analytics": report,
            "filename": filename
        })

    except Exception as e:
        logger.error(f"Analytics error for {filename}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/visualization/<filename>')
def visualization_page(filename):
    """Страница с визуализацией данных"""
    try:
        # Проверяем существование файла
        csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found for visualization page: {filename}")
            return "Файл не найден", 404

        # Проверяем наличие шаблона
        template_path = os.path.join(app.template_folder, 'visualization.html')
        if not os.path.exists(template_path):
            logger.error(f"Template visualization.html not found")
            # Возвращаем простую HTML страницу если шаблон отсутствует
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Визуализация</title></head>
            <body>
                <h1>Визуализация для файла: {filename}</h1>
                <p>Шаблон visualization.html не найден. Создайте файл templates/visualization.html</p>
                <a href="/">Вернуться на главную</a>
            </body>
            </html>
            """

        logger.info(f"Rendering visualization page for: {filename}")
        return render_template('visualization.html', csv_filename=filename)

    except Exception as e:
        logger.error(f"Error rendering visualization page: {str(e)}", exc_info=True)
        return f"Ошибка: {str(e)}", 500


@app.errorhandler(413)
def too_large(e):
    """Обработка превышения размера файла"""
    return jsonify({"error": "File too large. Maximum size is 100MB per file"}), 413


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

    logger.info("IFC Converter v1.2 with multiple file support initialized")
    return app


if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Проверяем development режим с ngrok
    ngrok_url = os.getenv('NGROK_URL')
    if ngrok_url:
        logger.info(f"Starting IFC Converter v1.2 in development mode")
        logger.info(f"Ngrok URL: {ngrok_url}")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        logger.info("Starting IFC Converter v1.2 on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)