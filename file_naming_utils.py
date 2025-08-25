#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для управления именами файлов с числовой индексацией
"""

import os
import re
#from pathlib import Path


def get_next_indexed_filename(directory, base_filename):
    """
    Получает следующее доступное имя файла с числовой индексацией

    :param directory: директория для проверки
    :param base_filename: базовое имя файла
    :return: уникальное имя файла
    """
    # Очищаем имя от недопустимых символов
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', base_filename)

    # Разделяем имя и расширение
    name_part = os.path.splitext(safe_filename)[0]
    ext_part = os.path.splitext(safe_filename)[1]

    # Полный путь к файлу
    full_path = os.path.join(directory, safe_filename)

    # Если файл не существует, возвращаем оригинальное имя
    if not os.path.exists(full_path):
        return safe_filename

    # Ищем следующий доступный индекс
    index = 1
    while True:
        indexed_filename = f"{name_part}_{index}{ext_part}"
        indexed_path = os.path.join(directory, indexed_filename)

        if not os.path.exists(indexed_path):
            return indexed_filename

        index += 1

        # Защита от бесконечного цикла (максимум 1000 файлов)
        if index > 1000:
            # Используем timestamp как fallback
            import uuid
            timestamp = uuid.uuid4().hex[:8]
            return f"{name_part}_{timestamp}{ext_part}"


def get_unique_sheet_name(spreadsheet, base_name):
    """
    Получает уникальное имя для листа Google Sheets с числовой индексацией

    :param spreadsheet: объект Google Spreadsheet
    :param base_name: базовое имя листа
    :return: уникальное имя листа
    """
    # Очищаем имя листа
    clean_name = sanitize_sheet_name(base_name)

    # Получаем список существующих листов
    existing_sheets = [worksheet.title for worksheet in spreadsheet.worksheets()]

    # Если имя уникально, возвращаем его
    if clean_name not in existing_sheets:
        return clean_name

    # Ищем следующий доступный индекс
    index = 1
    while True:
        indexed_name = f"{clean_name}_{index}"

        # Проверяем лимит длины Google Sheets (100 символов)
        if len(indexed_name) > 100:
            # Обрезаем базовое имя и добавляем индекс
            max_base_length = 100 - len(f"_{index}")
            truncated_base = clean_name[:max_base_length]
            indexed_name = f"{truncated_base}_{index}"

        if indexed_name not in existing_sheets:
            return indexed_name

        index += 1

        # Защита от бесконечного цикла
        if index > 1000:
            import uuid
            suffix = uuid.uuid4().hex[:6]
            return f"{clean_name[:90]}_{suffix}"


def sanitize_sheet_name(name):
    """
    Очищает имя листа от недопустимых символов для Google Sheets
    """
    # Удаляем расширение файла
    name = os.path.splitext(name)[0]

    # Google Sheets не разрешает некоторые символы в названиях листов
    # Заменяем недопустимые символы на underscore
    sanitized = re.sub(r'[^\w\-\.\s]', '_', name)

    # Убираем множественные подчеркивания
    sanitized = re.sub(r'_{2,}', '_', sanitized)

    # Убираем подчеркивания в начале и конце
    sanitized = sanitized.strip('_')

    # Ограничиваем длину (максимум 100 символов в Google Sheets)
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + "..."

    return sanitized or "Sheet"  # fallback если имя пустое