#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт квартир из IFC в CSV с поддержкой множественных файлов
Версия с исправленной логикой нумерации секций
"""

import sys
import csv
import re
import os
import glob
import ifcopenshell
import logging
from pathlib import Path
from file_naming_utils import get_next_indexed_filename

# Настройка логгера
logger = logging.getLogger('ifc-exporter')

# ------------------------------------------------------------
# универсальная функция получения p-сетов
# ------------------------------------------------------------
try:
    from ifcopenshell.util.element import get_psets as _get_psets  # nightly/0.7
except Exception:
    try:
        from ifcopenshell.util.pset import get_pset as _get_pset_single  # 0.6


        def _get_psets(ent):
            return {k: v for k, v in _get_pset_single(ent).items()}
    except Exception:
        def _get_psets(ent):  # fallback
            res = {}
            for rel in getattr(ent, "IsDefinedBy", []):
                if not rel.is_a("IfcRelDefinesByProperties"):
                    continue
                pset = rel.RelatingPropertyDefinition
                if not pset.is_a("IfcPropertySet"):
                    continue
                props = {}
                for p in pset.HasProperties:
                    if p.is_a("IfcPropertySingleValue") and p.NominalValue:
                        props[p.Name] = p.NominalValue.wrappedValue
                res[pset.Name] = props
            return res

# ------------------------------------------------------------
# константы
# ------------------------------------------------------------
ALLOWED_ZONE_TYPES = {
    "BRU_Zone_0С",
    "BRU_Zone_1С",
    "BRU_Zone_2С",
    "BRU_Zone_3С",
    "BRU_Zone_4С",
}

# Обновленный заголовок CSV с новыми столбцами
CSV_HEADER = [
    "FlatType",  # A - без префикса
    "Area_m2",  # B - исходная площадь
    "Area_m2'",  # C - скорректированная площадь (новый)
    "Section",  # D - без префикса
    "Section№",  # E - порядковый номер секции (новый)
    "FloorNum",  # F
    "StoreyName",  # G
    "FlatNumber",  # H
    "File",  # I - имя файла-источника (новый)
]

MILLI_METRE_FACTOR = 1.0  # 0.000001 — если площадь хранится в мм²

# Коэффициент площади по умолчанию
DEFAULT_AREA_COEFFICIENT = 0.9


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------
def get_flat_main_group(spatial_zone):
    """Получение основной группы квартиры"""
    for rel in getattr(spatial_zone, "HasAssignments", []):
        if rel.is_a("IfcRelAssignsToGroup") and rel.RelatingGroup.is_a("IfcZone"):
            return rel.RelatingGroup
    return None


def get_parent_of_type(element, ifc_type):
    """Поиск родительского элемента определенного типа"""
    cur = element
    visited = set()
    while cur and cur not in visited:
        visited.add(cur)
        for rel in getattr(cur, "Decomposes", []):
            if rel.is_a("IfcRelAggregates"):
                parent = rel.RelatingObject
                if parent.is_a(ifc_type):
                    return parent
                cur = parent
                break
        else:
            cur = None
    return None


def extract_floor_number(storey_name):
    """Извлечение номера этажа из названия"""
    m = re.search(r"э(\d+)", storey_name or "", flags=re.IGNORECASE)
    return int(m.group(1)) if m else ""


def extract_section_identifier(storey_name):
    """
    Извлечение уникального идентификатора секции из названия этажа
    Например: из "тб1_с1_э10" извлекаем "тб1_с1"
    """
    if not storey_name:
        return ""

    # Паттерн для извлечения тб<число>_с<число>
    match = re.match(r"(тб\d+_с\d+)", storey_name, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    # Альтернативный паттерн если нет тб
    match = re.match(r"(с\d+)", storey_name, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    return ""


def strip_prefix(value, prefix):
    """Удаление префикса из значения"""
    return value[len(prefix):] if value and value.startswith(prefix) else value


def get_area_value(group):
    """
    Получение площади с правильной обработкой единиц измерения
    """
    if not group:
        return ""

    psets = _get_psets(group)
    if "Pset_ZoneCommon" not in psets:
        return ""

    props = psets["Pset_ZoneCommon"]
    if "GrossPlannedArea" not in props:
        return ""

    area_value = props["GrossPlannedArea"]
    if isinstance(area_value, (int, float)):
        # Предполагаем, что площадь уже в м²
        formatted_area = str(round(float(area_value), 2)).replace('.', ',')
        logger.debug(f"Area processed: {area_value} -> {formatted_area}")
        return formatted_area

    return ""


def format_area_with_comma(area_value):
    """Форматирование площади с запятой для Excel"""
    if isinstance(area_value, (int, float)):
        return str(round(float(area_value), 2)).replace('.', ',')
    return str(area_value)


def calculate_corrected_area(area_str, coefficient):
    """
    Расчет скорректированной площади

    :param area_str: строка с площадью (может содержать запятую)
    :param coefficient: коэффициент корректировки
    :return: скорректированная площадь как строка с запятой
    """
    if not area_str:
        return ""

    try:
        # Заменяем запятую на точку для вычислений
        area_value = float(area_str.replace(',', '.'))
        corrected = area_value * coefficient
        # Возвращаем с запятой для Excel
        return str(round(corrected, 3)).replace('.', ',')
    except (ValueError, TypeError):
        return ""


def assign_section_numbers_improved(rows):
    """
    Улучшенное присваивание порядковых номеров секциям
    Сохраняет группировку по файлам, но обеспечивает сквозную нумерацию

    :param rows: список строк данных
    :return: обновленный список строк с номерами секций
    """
    # Собираем уникальные комбинации файл + идентификатор секции
    sections_order = []
    sections_map = {}
    file_sections = {}  # Для хранения секций по файлам

    # Сначала группируем секции по файлам
    for row in rows:
        storey_name = row[6]  # Столбец StoreyName
        file_name = row[8]  # Столбец File

        # Извлекаем идентификатор секции из StoreyName
        section_id = extract_section_identifier(storey_name)

        if section_id:
            if file_name not in file_sections:
                file_sections[file_name] = set()
            file_sections[file_name].add(section_id)

    # Теперь создаем сквозную нумерацию, но с учетом порядка файлов
    section_counter = 1
    for file_name in file_sections:
        for section_id in sorted(file_sections[file_name]):
            unique_key = f"{file_name}_{section_id}"
            sections_map[unique_key] = section_counter
            section_counter += 1

    # Обновляем строки с номерами секций
    for row in rows:
        storey_name = row[6]  # Столбец StoreyName
        file_name = row[8]  # Столбец File

        section_id = extract_section_identifier(storey_name)
        if section_id:
            unique_key = f"{file_name}_{section_id}"
            if unique_key in sections_map:
                row[4] = sections_map[unique_key]  # Столбец Section№
            else:
                row[4] = ""
        else:
            row[4] = ""

    return rows

def sort_rows_complex(rows):
    """
    Комплексная сортировка строк:
    1. Сначала по имени файла (сохраняем исходный порядок файлов)
    2. Затем по номеру секции
    3. Затем по этажу
    4. Затем по номеру квартиры
    """

    # Создаем mapping для порядка файлов
    file_order = {}
    current_order = 0
    for row in rows:
        file_name = row[8]  # File
        if file_name not in file_order:
            file_order[file_name] = current_order
            current_order += 1

    def sort_key(row):
        file_name = row[8]  # File
        section_num = row[4] if row[4] != "" else 999999  # Section№
        floor_num = row[5] if row[5] != "" else 999999  # FloorNum
        flat_number = str(row[7])  # FlatNumber

        # Извлекаем числовую часть из номера квартиры
        flat_match = re.match(r"(\d+)", flat_number)
        flat_num = int(flat_match.group(1)) if flat_match else 999999

        return (file_order[file_name], section_num, floor_num, flat_num, flat_number)

    rows.sort(key=sort_key)


def process_single_ifc(ifc_path, area_coefficient=DEFAULT_AREA_COEFFICIENT):
    """
    Обработка одного IFC файла

    :param ifc_path: путь к IFC файлу
    :param area_coefficient: коэффициент корректировки площади
    :return: список строк данных
    """
    try:
        logger.info(f"Processing IFC file: {ifc_path}")
        model = ifcopenshell.open(ifc_path)
        logger.info(f"IFC model loaded successfully. Schema: {model.schema}")
    except Exception as e:
        logger.error(f"Error opening IFC file: {str(e)}")
        raise ValueError(f"Failed to open IFC file: {str(e)}")

    rows = []
    processed_zones = 0

    # Получаем имя файла без пути и расширения
    file_name = Path(ifc_path).stem

    # Обработка всех зон в модели
    logger.info("Starting zone processing...")

    for zone in model.by_type("IfcSpatialZone"):
        zone_type = (zone.ObjectType or "").strip()

        if zone_type not in ALLOWED_ZONE_TYPES:
            logger.debug(f"Skipping zone with type: {zone_type}")
            continue

        processed_zones += 1

        # Извлечение типа квартиры (убираем префикс)
        flat_type = strip_prefix(zone_type, "BRU_Zone_")
        flat_number = zone.Name or ""

        # Получение площади через группу
        group = get_flat_main_group(zone)
        area = get_area_value(group)

        # Альтернативный способ получения площади
        if group and not area:
            psets = _get_psets(group)
            if "Pset_ZoneCommon" in psets:
                props = psets["Pset_ZoneCommon"]
                if "GrossPlannedArea" in props:
                    try:
                        area_num = float(props["GrossPlannedArea"]) * MILLI_METRE_FACTOR
                        area = format_area_with_comma(area_num)
                        logger.debug(f"Alternative area calculation: {area}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to process area value: {e}")

        # Расчет скорректированной площади
        corrected_area = calculate_corrected_area(area, area_coefficient)

        # Получение информации об этаже
        storey = get_parent_of_type(zone, "IfcBuildingStorey")
        storey_name = storey.Name if storey else ""
        floor_num = extract_floor_number(storey_name)

        # Получение информации о секции
        section = get_parent_of_type(storey, "IfcSpatialStructureElement") if storey else None
        section_clean = ""
        if section and section.ObjectType:
            section_clean = strip_prefix(section.ObjectType, "BRU_Секция_")

        # Добавление строки данных с новыми столбцами
        row_data = [
            flat_type,  # A - FlatType
            area,  # B - Area_m2
            corrected_area,  # C - Area_m2' (новый)
            section_clean,  # D - Section
            "",  # E - Section№ (будет заполнен позже)
            floor_num,  # F - FloorNum
            storey_name,  # G - StoreyName
            flat_number,  # H - FlatNumber
            file_name,  # I - File (новый)
        ]

        rows.append(row_data)
        logger.debug(f"Processed flat: {flat_number}, type: {flat_type}, area: {area}, storey: {storey_name}")

    logger.info(f"Processed {processed_zones} zones from {file_name}")
    return rows


def export_flats_multiple(ifc_paths, download_dir, area_coefficient=DEFAULT_AREA_COEFFICIENT,
                          combined_filename=None):
    """
    Обработка нескольких IFC файлов с объединением результатов

    :param ifc_paths: список путей к IFC файлам
    :param download_dir: папка для сохранения CSV
    :param area_coefficient: коэффициент корректировки площади
    :param combined_filename: имя для объединенного файла
    :return: путь к созданному CSV файлу
    """
    if not ifc_paths:
        raise ValueError("No IFC files provided")

    all_rows = []

    # Обрабатываем каждый файл
    for ifc_path in ifc_paths:
        try:
            rows = process_single_ifc(ifc_path, area_coefficient)
            all_rows.extend(rows)
        except Exception as e:
            logger.error(f"Failed to process {ifc_path}: {str(e)}")
            # Продолжаем с остальными файлами
            continue

    if not all_rows:
        raise ValueError("No data extracted from IFC files")

    # Присваиваем номера секциям с улучшенной логикой
    all_rows = assign_section_numbers_improved(all_rows)

    # Комплексная сортировка: по файлу, секции, этажу, квартире
    sort_rows_complex(all_rows)

    # Создание папки для скачивания
    os.makedirs(download_dir, exist_ok=True)

    # Формирование имени файла
    if combined_filename:
        csv_base_filename = f"{combined_filename}.csv"
    elif len(ifc_paths) == 1:
        base_name = Path(ifc_paths[0]).stem
        csv_base_filename = f"{base_name}.csv"
    else:
        csv_base_filename = "combined_export.csv"

    # Получаем уникальное имя
    csv_filename = get_next_indexed_filename(download_dir, csv_base_filename)
    csv_path = os.path.join(download_dir, csv_filename)

    # Запись CSV
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_HEADER)
            writer.writerows(all_rows)

        logger.info(f"Successfully exported {len(all_rows)} flats to {csv_path}")

        # Проверка файла
        if not os.path.exists(csv_path):
            raise Exception("CSV file was not created")

        file_size = os.path.getsize(csv_path)
        if file_size == 0:
            raise Exception("CSV file is empty")

        logger.info(f"CSV file created: {csv_filename} ({file_size} bytes)")

    except Exception as e:
        logger.error(f"CSV write error: {str(e)}")
        raise Exception(f"Failed to write CSV file: {str(e)}")

    return csv_path


# Обратная совместимость - оставляем старую функцию
def export_flats(ifc_path, download_dir, original_filename=None):
    """
    Обрабатывает IFC-файл и сохраняет CSV (обратная совместимость)
    """
    return export_flats_multiple([ifc_path], download_dir,
                                 DEFAULT_AREA_COEFFICIENT,
                                 original_filename)