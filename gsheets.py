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

def upload_to_google_sheets(csv_path, original_filename):
    """Загрузка CSV в Google Sheets с созданием новой таблицы"""
    try:
        # Авторизация через сервисный аккаунт
        scope = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive']

        creds = ServiceAccountCredentials.from_json_keyfile_dict({
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
        }, scope)

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
                # Обновление заголовков
                worksheet.update('A1', [data[0]])

                # Обновление данных
                if len(data) > 1:
                    worksheet.update(f'A2:{chr(65 + len(data[0])}{len(data)}', data[1:])
        
        logger.info(f"Data uploaded: {len(data)-1} rows")
        return spreadsheet.url

    except Exception as e:
        logger.error(f"Google Sheets upload error: {str(e)}", exc_info=True)
        raise