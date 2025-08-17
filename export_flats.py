#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт квартир из IFC в CSV (обновленная версия для Flask API)
"""

import sys
import csv
import re
import os
import glob
import ifcopenshell
import logging
from pathlib import Path

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
    for rel in getattr(spatial_zone, "HasAssignments", []):
        if rel.is_a("IfcRelAssignsToGroup") and rel.RelatingGroup.is_a("IfcZone"):
            return rel.RelatingGroup
    return None


def get_parent_of_type(element, ifc_type):
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
    m = re.search(r"э(\d+)", storey_name or "", flags=re.IGNORECASE)
    return int(m.group(1)) if m else ""


def strip_prefix(value, prefix):
    return value[len(prefix):] if value and value.startswith(prefix) else value


def sort_rows_by_flat_number(rows):
    def key(row):
        num = str(row[5])  # FlatNumber теперь последний в списке
        m = re.match(r"\d+", num)
        return (int(m.group()) if m else float("inf"), num)

    rows.sort(key=key)


# Обработка площади
def get_area_value(group):
    """Получение площади с правильной обработкой единиц измерения"""
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
        return str(round(float(area_value), 2)).replace('.', ',')

    return ""

def format_area_with_comma(area_value):
    """Вспомогательная функция для форматирования площади с запятой"""
    if isinstance(area_value, (int, float)):
        return str(round(float(area_value), 2)).replace('.', ',')
    return str(area_value)

# ------------------------------------------------------------
# основная обработка
# ------------------------------------------------------------
def export_flats(ifc_path, download_dir, original_filename=None):
    """
    Обрабатывает IFC-файл и сохраняет CSV в папке для скачивания

    :param ifc_path: Путь к входному IFC-файлу в папке uploads
    :param download_dir: Папка для сохранения CSV (downloads)
    :return: Абсолютный путь к созданному CSV-файлу
    """
    try:
        logger.info(f"Processing IFC file: {ifc_path}")
        model = ifcopenshell.open(ifc_path)
    except Exception as e:
        logger.error(f"Error opening IFC file: {str(e)}")
        raise

    rows = []

    # Обработка всех зон в модели
    for zone in model.by_type("IfcSpatialZone"):
        if (zone.ObjectType or "").strip() not in ALLOWED_ZONE_TYPES:
            continue

        flat_type = strip_prefix(zone.ObjectType.strip(), "BRU_Zone_")
        flat_number = zone.Name or ""

        # Получение площади
        group = get_flat_main_group(zone)
        area = get_area_value(group)
        if group and not area:  # если get_area_value не вернула результат, пробуем альтернативный способ
            psets = _get_psets(group)
            if "Pset_ZoneCommon" in psets:
                props = psets["Pset_ZoneCommon"]
                if "GrossPlannedArea" in props:
                    area_num = float(props["GrossPlannedArea"]) * MILLI_METRE_FACTOR
                    area = format_area_with_comma(area_num)

        # Получение информации об этаже
        storey = get_parent_of_type(zone, "IfcBuildingStorey")
        storey_name = storey.Name if storey else ""
        floor_num = extract_floor_number(storey_name)

        # Получение информации о секции
        section = get_parent_of_type(storey, "IfcSpatialStructureElement") if storey else None
        section_clean = strip_prefix(section.ObjectType, "BRU_Секция_") if section and section.ObjectType else ""

        # Добавление строки данных
        rows.append([
            flat_type,
            area,
            section_clean,
            floor_num,
            storey_name,
            flat_number
        ])

    # Сортировка по номеру квартиры
    sort_rows_by_flat_number(rows)

    # Создание папки для скачивания, если не существует
    os.makedirs(download_dir, exist_ok=True)

    # Формирование пути для CSV - используем оригинальное имя файла
    if original_filename:
        # Убираем расширение из оригинального имени и добавляем .csv
        base_name = os.path.splitext(original_filename)[0]
        # Очищаем имя от недопустимых символов для файловой системы
        import re
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
        csv_filename = f"{base_name}.csv"
    else:
        # Fallback к старому способу
        base_name = Path(ifc_path).stem
        csv_filename = f"{base_name}.csv"

    csv_path = os.path.join(download_dir, csv_filename)

    # Запись CSV
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
        logger.info(f"Exported {len(rows)} flats to {csv_path}")
    except Exception as e:
        logger.error(f"CSV write error: {str(e)}")
        raise

    return csv_path


# Функция main для автономного использования (если нужно)
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
    download_dir = os.path.join(script_dir, "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Обработка файлов
    for ifc_path in paths:
        if not os.path.isfile(ifc_path):
            print(f"! Файл не найден: {ifc_path}")
            continue
        try:
            csv_path = export_flats(ifc_path, download_dir)
            print(f"Success: {csv_path}")
        except Exception as e:
            print(f"Error processing {ifc_path}: {str(e)}")


if __name__ == "__main__":
    main()