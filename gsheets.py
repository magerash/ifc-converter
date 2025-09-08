"""
Обновленный модуль для работы с Google Sheets API
Включает форматирование столбцов и выравнивание
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import csv
import logging
import re
from datetime import datetime
from file_naming_utils import get_unique_sheet_name, sanitize_sheet_name

# Настройка логгера
logger = logging.getLogger('ifc-exporter')

# Попытка загрузки переменных из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Environment variables loaded from .env file")
except ImportError:
    logger.info("python-dotenv not installed, using system environment variables")


def clean_numeric_value(value):
    """
    Очистка числовых значений от апострофов, но сохранение запятой как разделителя
    """
    if not value or not isinstance(value, str):
        return value

    # Удаляем апостроф в начале строки
    if value.startswith("'"):
        value = value[1:]

    return value


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


def upload_to_google_sheets(csv_path, original_filename, area_coefficient=0.9):
    """
    Загрузка CSV в существующую Google Sheets таблицу как новую вкладку
    с правильным форматированием столбцов

    :param csv_path: путь к CSV файлу
    :param original_filename: оригинальное имя IFC файла ИЛИ уже сформированное имя для объединенных файлов
    :param area_coefficient: коэффициент площади, использованный при обработке
    :return: URL таблицы
    """

    try:
        validate_gs_credentials()

        # ID существующей таблицы
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

        # ВАЖНОЕ ИЗМЕНЕНИЕ: Используем original_filename напрямую, так как он уже правильно сформирован
        # в main.py через generate_combined_filename()
        logger.info(f"Received original_filename for sheet: {original_filename}")

        # Просто санитизируем его для Google Sheets (убираем недопустимые символы)
        base_sheet_name = sanitize_sheet_name(original_filename)
        logger.info(f"After sanitization: {base_sheet_name}")

        # Получаем уникальное имя для новой вкладки (добавит индекс если такое имя уже есть)
        sheet_name = get_unique_sheet_name(spreadsheet, base_sheet_name)
        logger.info(f"Final sheet name: {sheet_name}")

        # Создаем новую вкладку с достаточным количеством столбцов для S и T
        try:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)  # Увеличили количество столбцов
            logger.info(f"Created new worksheet: {sheet_name}")
        except Exception as e:
            logger.error(f"Failed to create worksheet: {str(e)}")
            raise

        # Чтение и очистка данных из CSV
        data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f, delimiter=';')
            for row in csv_reader:
                # Очищаем числовые значения от апострофов
                cleaned_row = []
                for i, value in enumerate(row):
                    # Для числовых столбцов (B, C, E, F) применяем очистку
                    if i in [1, 2, 4, 5]:  # Индексы столбцов B, C, E, F (начиная с 0)
                        cleaned_value = clean_numeric_value(value)
                        cleaned_row.append(cleaned_value)
                    else:
                        cleaned_row.append(value)
                data.append(cleaned_row)

        if data:
            # Определяем размер данных
            num_rows = len(data)
            num_cols = len(data[0]) if data else 0

            # Batch операция для всех данных
            if num_cols > 0:
                # Определяем конечный столбец (A=1, B=2, ..., I=9)
                end_col = chr(65 + num_cols - 1)  # Для 9 столбцов это будет 'I'
                range_name = f'A1:{end_col}{num_rows}'

                worksheet.update(range_name, data)
                logger.info(f"Data uploaded to worksheet '{sheet_name}': {num_rows - 1} data rows, {num_cols} columns")

        # Устанавливаем ширину всех столбцов в 103 пикселя
        try:
            if num_cols > 0:
                requests = []
                for col_index in range(num_cols):
                    requests.append({
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": worksheet.id,
                                "dimension": "COLUMNS",
                                "startIndex": col_index,
                                "endIndex": col_index + 1
                            },
                            "properties": {
                                "pixelSize": 103
                            },
                            "fields": "pixelSize"
                        }
                    })

                # Также устанавливаем ширину для столбцов S и T (индексы 18 и 19)
                for col_index in [18, 19]:  # S и T
                    requests.append({
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": worksheet.id,
                                "dimension": "COLUMNS",
                                "startIndex": col_index,
                                "endIndex": col_index + 1
                            },
                            "properties": {
                                "pixelSize": 150  # Чуть шире для метаданных
                            },
                            "fields": "pixelSize"
                        }
                    })

                spreadsheet.batch_update({"requests": requests})
                logger.info(f"Set columns width: data columns to 103px, metadata columns to 150px")
        except Exception as e:
            logger.warning(f"Failed to set column width: {str(e)}")

        # Форматирование заголовков с цветами
        try:
            if data and len(data) > 0:
                # Определяем диапазон заголовков
                header_range = f'A1:{chr(65 + len(data[0]) - 1)}1'

                # Базовое форматирование для всех заголовков
                base_format = {
                    'textFormat': {
                        'bold': True,
                        'fontSize': 10
                    },
                    'horizontalAlignment': 'LEFT',
                    'verticalAlignment': 'MIDDLE',
                    'borders': {
                        'top': {'style': 'SOLID'},
                        'bottom': {'style': 'SOLID'},
                        'left': {'style': 'SOLID'},
                        'right': {'style': 'SOLID'}
                    },
                    'backgroundColor': {
                        'red': 0.9529,
                        'green': 0.9529,
                        'blue': 0.9529
                    }
                }

                # Применяем базовое форматирование
                worksheet.format(header_range, base_format)
                logger.info("Header formatting applied")

        except Exception as e:
            logger.warning(f"Failed to format headers: {str(e)}")

        # Форматирование типов данных для столбцов
        try:
            if num_rows > 1:  # Если есть данные помимо заголовка
                # Текстовые столбцы: A, D, G, H, I
                text_columns = ['A', 'D', 'G', 'H', 'I']
                for col in text_columns:
                    range_str = f'{col}2:{col}{num_rows}'
                    worksheet.format(range_str, {
                        'numberFormat': {'type': 'TEXT'},
                        'horizontalAlignment': 'LEFT'
                    })

                # Числовые столбцы: B, C, E, F
                number_columns = ['B', 'C', 'E', 'F']
                for col in number_columns:
                    range_str = f'{col}2:{col}{num_rows}'
                    worksheet.format(range_str, {
                        'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'},
                        'horizontalAlignment': 'LEFT'
                    })

                logger.info("Column data types formatted")

        except Exception as e:
            logger.warning(f"Failed to format column data types: {str(e)}")

        # Выравнивание всех данных по левой стороне
        try:
            if num_rows > 1:
                full_range = f'A2:{chr(65 + num_cols - 1)}{num_rows}'
                worksheet.format(full_range, {'horizontalAlignment': 'LEFT'})
                logger.info("Left alignment applied to all data")
        except Exception as e:
            logger.warning(f"Failed to apply alignment: {str(e)}")

        # Добавляем информацию о дате создания и коэффициенте в ячейки S и T
        try:
            # Заголовки в S1 и T1
            headers_data = [
                ['Создано', 'Коэффициент площади']
            ]
            worksheet.update('S1:T1', headers_data)

            # Форматирование заголовков
            worksheet.format('S1:T1', {
                'textFormat': {
                    'bold': True,
                    'fontSize': 10
                },
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE',
                'borders': {
                    'top': {'style': 'SOLID'},
                    'bottom': {'style': 'SOLID'},
                    'left': {'style': 'SOLID'},
                    'right': {'style': 'SOLID'}
                },
                'backgroundColor': {
                    'red': 0.9529,
                    'green': 0.9529,
                    'blue': 0.9529
                }
            })

            # Данные в S2 и T2
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            # Форматируем коэффициент с запятой для Excel
            coefficient_str = str(area_coefficient).replace('.', ',')
            values_data = [
                [timestamp, coefficient_str]
            ]
            worksheet.update('S2:T2', values_data)

            # Форматирование данных
            worksheet.format('S2', {
                'textFormat': {
                    'fontSize': 9
                },
                'horizontalAlignment': 'CENTER',
                'borders': {
                    'top': {'style': 'SOLID'},
                    'bottom': {'style': 'SOLID'},
                    'left': {'style': 'SOLID'},
                    'right': {'style': 'SOLID'}
                }
            })

            worksheet.format('T2', {
                'textFormat': {
                    'fontSize': 9
                },
                'horizontalAlignment': 'CENTER',
                'borders': {
                    'top': {'style': 'SOLID'},
                    'bottom': {'style': 'SOLID'},
                    'left': {'style': 'SOLID'},
                    'right': {'style': 'SOLID'}
                }
            })

            logger.info(f"Added metadata: timestamp={timestamp}, coefficient={area_coefficient}")

        except Exception as e:
            logger.warning(f"Failed to add metadata cells: {str(e)}")

        # Возвращаем URL конкретной вкладки
        worksheet_url = f"{spreadsheet.url}#gid={worksheet.id}"
        logger.info(f"Successfully created worksheet with URL: {worksheet_url}")
        return worksheet_url

    except Exception as e:
        logger.error(f"Google Sheets upload error: {str(e)}", exc_info=True)
        raise