"""
Модуль для работы с Google Sheets API
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import csv
import logging
import re
from datetime import datetime

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
        'GS_CLIENT_EMAIL', 'GS_CLIENT_ID', 'GS_AUTH_URI', 'GS_TOKEN_URI', 'GS_SPREADSHEET_ID'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing environment variables: {missing}")

    # Проверка, что ключи не являются placeholder'ами
    if os.getenv('GS_PROJECT_ID', '').startswith('your-'):
        raise ValueError("Please replace placeholder values in .env file with actual Google API credentials")
def sanitize_sheet_name(name):
    """
    Очищает имя листа от недопустимых символов для Google Sheets
    """
    # Удаляем расширение файла
    name = os.path.splitext(name)[0]

    # Google Sheets не разрешает некоторые символы в названиях листов
    # Заменяем недопустимые символы на underscore
    sanitized = re.sub(r'[^\w\-\.\s]', '_', name)

    # Ограничиваем длину (максимум 100 символов в Google Sheets)
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."

    return sanitized

def upload_to_google_sheets(csv_path, original_filename):
    """
    Загрузка CSV в существующую Google Sheets таблицу как новую вкладку

    :param csv_path: путь к CSV файлу
    :param original_filename: оригинальное имя IFC файла
    :return: URL таблицы
    """

    try:
        validate_gs_credentials()

        # ID существующей таблицы (нужно указать в переменных окружения)
        spreadsheet_id = os.getenv('GS_SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError(
                "Missing GS_SPREADSHEET_ID environment variable. Please specify the ID of existing Google Sheets document.")

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

        # Открываем существующую таблицу
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
            logger.info(f"Opened existing spreadsheet: {spreadsheet.title}")
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet with ID {spreadsheet_id} not found. Check GS_SPREADSHEET_ID.")
        except gspread.exceptions.APIError as e:
            if "PERMISSION_DENIED" in str(e):
                raise ValueError(
                    f"No access to spreadsheet {spreadsheet_id}. Check sharing permissions for service account email: {creds_dict['client_email']}")
            raise

        # Создаем имя для новой вкладки
        sheet_name = sanitize_sheet_name(original_filename)

        # Проверяем, существует ли уже вкладка с таким именем
        existing_sheets = [worksheet.title for worksheet in spreadsheet.worksheets()]

        if sheet_name in existing_sheets:
            # Если вкладка существует, добавляем временную метку
            timestamp = datetime.now().strftime("_%H%M%S")
            sheet_name = f"{sheet_name}{timestamp}"
            logger.info(f"Sheet name already exists, using: {sheet_name}")

        # Создаем новую вкладку
        try:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
            logger.info(f"Created new worksheet: {sheet_name}")
        except Exception as e:
            logger.error(f"Failed to create worksheet: {str(e)}")
            raise

        # Чтение и загрузка данных из CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f, delimiter=';')
            data = list(csv_reader)

        if data:
            # Batch операция для всех данных сразу
            range_name = f'A1:{chr(65 + len(data[0]) - 1)}{len(data)}'
            worksheet.update(range_name, data)
            logger.info(f"Data uploaded to worksheet '{sheet_name}': {len(data) - 1} rows")

        # Форматируем заголовки (делаем их жирными)
        try:
            worksheet.format('A1:F1', {'textFormat': {'bold': True}})
            logger.info("Header formatting applied")
        except Exception as e:
            logger.warning(f"Failed to format headers: {str(e)}")

        # Возвращаем URL конкретной вкладки
        worksheet_url = f"{spreadsheet.url}#gid={worksheet.id}"
        return worksheet_url

    except Exception as e:
        logger.error(f"Google Sheets upload error: {str(e)}", exc_info=True)
        raise