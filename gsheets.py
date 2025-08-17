"""
Модуль для работы с Google Sheets API
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import csv
import logging

# Настройка логгера
logger = logging.getLogger('ifc-exporter')

# Попытка загрузки переменных из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Environment variables loaded from .env file")
except ImportError:
    logger.info("python-dotenv not installed, using system environment variables")

def validate_gs_credentials():
    """Проверка наличия всех необходимых переменных окружения"""
    required_vars = [
        'GS_TYPE', 'GS_PROJECT_ID', 'GS_PRIVATE_KEY_ID', 'GS_PRIVATE_KEY',
        'GS_CLIENT_EMAIL', 'GS_CLIENT_ID', 'GS_AUTH_URI', 'GS_TOKEN_URI'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing environment variables: {missing}")

    # Проверка, что ключи не являются placeholder'ами
    if os.getenv('GS_PROJECT_ID', '').startswith('your-'):
        raise ValueError("Please replace placeholder values in .env file with actual Google API credentials")

def upload_to_google_sheets(csv_path, original_filename):
    """Загрузка CSV в Google Sheets с созданием новой таблицы"""
    try:
        validate_gs_credentials()  # Проверка перед началом
        # Авторизация через сервисный аккаунт
        scope = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive']

        creds_dict = {
            "type": os.getenv("GS_TYPE"),
            "project_id": os.getenv("GS_PROJECT_ID"),
            "private_key_id": os.getenv("GS_PRIVATE_KEY_ID"),
            "private_key": os.getenv("GS_PRIVATE_KEY").replace('\\n', '\n'),
            "client_email": os.getenv("GS_CLIENT_EMAIL"),
            "client_id": os.getenv("GS_CLIENT_ID"),
            "auth_uri": os.getenv("GS_AUTH_URI"),
            "token_uri": os.getenv("GS_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("GS_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("GS_CLIENT_X509_CERT_URL")
        }

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        logger.info("Authenticated with Google Sheets API")

        # Создание новой таблицы
        spreadsheet_name = f"IFC Export: {os.path.splitext(original_filename)[0]}"
        spreadsheet = client.create(spreadsheet_name)
        logger.info(f"Created new spreadsheet: {spreadsheet_name}")

        # Настройка доступа
        spreadsheet.share(None, perm_type='anyone', role='writer')

        # Получение первого листа
        worksheet = spreadsheet.get_worksheet(0)
        worksheet.update_title("Квартирография")
        logger.info("Worksheet prepared")

        # Чтение и загрузка данных из CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f, delimiter=';')
            data = list(csv_reader)

        if data:
            # Batch операция для всех данных сразу
            range_name = f'A1:{chr(65 + len(data[0]) - 1)}{len(data)}'
            worksheet.update(range_name, data)

        logger.info(f"Data uploaded: {len(data) - 1} rows")
        return spreadsheet.url

    except Exception as e:
        logger.error(f"Google Sheets upload error: {str(e)}", exc_info=True)
        raise