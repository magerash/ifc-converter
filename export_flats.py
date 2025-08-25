#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт квартир из IFC в CSV с улучшенной системой именования файлов
Обновленная версия с поддержкой числовой индексации
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

CSV_HEADER = [
    "FlatType",  # без префикса
    "Area_m2",
    "Section",  # без префикса
    "FloorNum",
    "StoreyName",
    "FlatNumber",
]

MILLI_METRE_FACTOR = 1.0  # 0.000001 — если площадь хранится в мм²


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


def strip_prefix(value, prefix):
    """Удаление префикса из значения"""
    return value[len(prefix):] if value and value.startswith(prefix) else value


def sort_rows_by_flat_number(rows):
    """Сортировка строк по номеру квартиры"""

    def key(row):
        num = str(row[5])  # FlatNumber теперь последний в списке
        m = re.match(r"\d+", num)
        return (int(m.group()) if m else float("inf"), num)

    rows.sort(key=key)


def get_area_value(group):
    """
    Получение площади с правильной обработкой единиц измерения
    Улучшенная версия с обработкой различных форматов
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


def count_csv_rows(csv_path):
    """Подсчет количества строк данных в CSV файле (исключая заголовок)"""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Подсчитываем строки, исключая заголовок
            return sum(1 for line in f) - 1
    except Exception as e:
        logger.warning(f"Failed to count CSV rows: {str(e)}")
        return 0


# ------------------------------------------------------------
# основная обработка
# ------------------------------------------------------------
def export_flats(ifc_path, download_dir, original_filename=None):
    """
    Обрабатывает IFC-файл и сохраняет CSV в папке для скачивания
    Использует улучшенную систему именования с числовой индексацией

    :param ifc_path: Путь к входному IFC-файлу в папке uploads
    :param download_dir: Папка для сохранения CSV (downloads)
    :param original_filename: Оригинальное имя файла для сохранения структуры
    :return: Абсолютный путь к созданному CSV-файлу
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

        # Альтернативный способ получения площади, если основной не сработал
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

        # Получение информации об этаже
        storey = get_parent_of_type(zone, "IfcBuildingStorey")
        storey_name = storey.Name if storey else ""
        floor_num = extract_floor_number(storey_name)

        # Получение информации о секции
        section = get_parent_of_type(storey, "IfcSpatialStructureElement") if storey else None
        section_clean = ""
        if section and section.ObjectType:
            section_clean = strip_prefix(section.ObjectType, "BRU_Секция_")

        # Добавление строки данных
        row_data = [
            flat_type,
            area,
            section_clean,
            floor_num,
            storey_name,
            flat_number
        ]

        rows.append(row_data)
        logger.debug(f"Processed flat: {flat_number}, type: {flat_type}, area: {area}")

    logger.info(f"Processed {processed_zones} zones, generated {len(rows)} flat records")

    # Сортировка по номеру квартиры
    sort_rows_by_flat_number(rows)

    # Создание папки для скачивания, если не существует
    os.makedirs(download_dir, exist_ok=True)

    # Формирование уникального пути для CSV с использованием улучшенной системы именования
    if original_filename:
        # Используем оригинальное имя файла как основу
        base_name = os.path.splitext(original_filename)[0]
        csv_base_filename = f"{base_name}.csv"
    else:
        # Fallback к старому способу
        base_name = Path(ifc_path).stem
        csv_base_filename = f"{base_name}.csv"

    # Получаем уникальное имя с числовой индексацией
    csv_filename = get_next_indexed_filename(download_dir, csv_base_filename)
    csv_path = os.path.join(download_dir, csv_filename)

    # Запись CSV с улучшенной обработкой ошибок
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)

        logger.info(f"Successfully exported {len(rows)} flats to {csv_path}")

        # Проверяем, что файл действительно создан и содержит данные
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


def export_flats_with_stats(ifc_path, download_dir, original_filename=None):
    """
    Расширенная версия функции экспорта с дополнительной статистикой

    :param ifc_path: Путь к входному IFC-файлу
    :param download_dir: Папка для сохранения CSV
    :param original_filename: Оригинальное имя файла
    :return: Словарь с результатами и статистикой
    """
    start_time = time.time()

    try:
        # Основной экспорт
        csv_path = export_flats(ifc_path, download_dir, original_filename)

        # Сбор статистики
        processing_time = time.time() - start_time
        processed_flats = count_csv_rows(csv_path)
        file_size = os.path.getsize(csv_path) if os.path.exists(csv_path) else 0

        # Анализ содержимого CSV для дополнительной статистики
        stats = analyze_csv_content(csv_path)

        return {
            'success': True,
            'csv_path': csv_path,
            'csv_filename': os.path.basename(csv_path),
            'processing_time': round(processing_time, 2),
            'processed_flats': processed_flats,
            'file_size': file_size,
            'stats': stats
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Export failed after {processing_time:.2f}s: {str(e)}")

        return {
            'success': False,
            'error': str(e),
            'processing_time': round(processing_time, 2),
            'processed_flats': 0,
            'file_size': 0
        }


def analyze_csv_content(csv_path):
    """
    Анализ содержимого CSV файла для получения статистики

    :param csv_path: Путь к CSV файлу
    :return: Словарь со статистикой
    """
    stats = {
        'flat_types': {},
        'sections': set(),
        'floors': set(),
        'total_area': 0.0,
        'flats_with_area': 0
    }

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                # Статистика по типам квартир
                flat_type = row.get('FlatType', '')
                if flat_type:
                    stats['flat_types'][flat_type] = stats['flat_types'].get(flat_type, 0) + 1

                # Статистика по секциям
                section = row.get('Section', '')
                if section:
                    stats['sections'].add(section)

                # Статистика по этажам
                floor = row.get('FloorNum', '')
                if floor:
                    stats['floors'].add(str(floor))

                # Статистика по площадям
                area_str = row.get('Area_m2', '').replace(',', '.')
                if area_str:
                    try:
                        area = float(area_str)
                        stats['total_area'] += area
                        stats['flats_with_area'] += 1
                    except ValueError:
                        pass

        # Преобразуем sets в списки для JSON сериализации
        stats['sections'] = sorted(list(stats['sections']))
        stats['floors'] = sorted(list(stats['floors']), key=lambda x: int(x) if x.isdigit() else 0)
        stats['average_area'] = round(stats['total_area'] / stats['flats_with_area'], 2) if stats[
                                                                                                'flats_with_area'] > 0 else 0

        logger.info(f"CSV analysis complete: {len(stats['flat_types'])} flat types, {len(stats['sections'])} sections")

    except Exception as e:
        logger.warning(f"Failed to analyze CSV content: {str(e)}")

    return stats


# Импорт для измерения времени
import time


# Функция main для автономного использования
def main():
    """Автономный режим работы (для тестирования)"""
    # Пути, заданные пользователем
    paths = sys.argv[1:]

    # Если не указаны - ищем в текущей директории
    if not paths:
        script_dir = os.path.dirname(os.path.realpath(__file__)) or "."
        uploads_dir = os.path.join(script_dir, "uploads")
        paths = sorted(
            glob.glob(os.path.join(uploads_dir, "*.ifc")) +
            glob.glob(os.path.join(uploads_dir, "*.ifczip"))
        )
        if not paths:
            print("Файлы *.ifc / *.ifczip не найдены.")
            return

    # Создаем папку для скачивания в текущей директории
    script_dir = os.path.dirname(os.path.realpath(__file__)) or "."
    download_dir = os.path.join(script_dir, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Обработка файлов
    for ifc_path in paths:
        if not os.path.isfile(ifc_path):
            print(f"! Файл не найден: {ifc_path}")
            continue

        try:
            print(f"Обработка: {os.path.basename(ifc_path)}")
            result = export_flats_with_stats(ifc_path, download_dir)

            if result['success']:
                print(f"✅ Успешно: {result['csv_filename']}")
                print(f"   Квартир: {result['processed_flats']}")
                print(f"   Время: {result['processing_time']}с")
                print(f"   Размер: {result['file_size']} байт")
                if 'stats' in result:
                    stats = result['stats']
                    print(f"   Типы квартир: {', '.join(stats['flat_types'].keys())}")
                    print(f"   Секций: {len(stats['sections'])}")
            else:
                print(f"❌ Ошибка: {result['error']}")

        except Exception as e:
            print(f"❌ Ошибка обработки {ifc_path}: {str(e)}")


if __name__ == "__main__":
    main()