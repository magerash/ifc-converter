#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт квартир из IFC в CSV.
Если пути к моделям не указаны, скрипт ищет *.ifc / *.ifczip
в директории, где расположен скрипт, и обрабатывает их все.

Колонки CSV: FlatType, FlatNumber, Area_m2, StoreyName, FloorNum, Section
"""

import sys
import csv
import re
import os
import glob
import ifcopenshell

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
    "FlatType",     # без префикса
    "FlatNumber",
    "Area_m2",
    "StoreyName",
    "FloorNum",
    "Section"       # без префикса
]

MILLI_METRE_FACTOR = 1.0   # 0.000001 — если площадь хранится в мм²

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
        num = str(row[1])  # FlatNumber
        m = re.match(r"\d+", num)
        return (int(m.group()) if m else float("inf"), num)
    rows.sort(key=key)


# ------------------------------------------------------------
# основная обработка
# ------------------------------------------------------------
def export_flats(ifc_path, csv_path):
    print(f"→ {os.path.basename(ifc_path)}", end=" ... ")
    try:
        model = ifcopenshell.open(ifc_path)
    except Exception as e:
        print(f"ошибка открытия: {e}")
        return

    rows = []

    for zone in model.by_type("IfcSpatialZone"):
        if (zone.ObjectType or "").strip() not in ALLOWED_ZONE_TYPES:
            continue

        flat_type = strip_prefix(zone.ObjectType.strip(), "BRU_Zone_")
        flat_number = zone.Name or ""

        # площадь
        area = ""
        group = get_flat_main_group(zone)
        if group:
            psets = _get_psets(group)
            if "Pset_ZoneCommon" in psets:
                props = psets["Pset_ZoneCommon"]
                if "GrossPlannedArea" in props:
                    area = float(props["GrossPlannedArea"]) * MILLI_METRE_FACTOR

        # этаж и секция
        storey = get_parent_of_type(zone, "IfcBuildingStorey")
        storey_name = storey.Name if storey else ""
        floor_num = extract_floor_number(storey_name)

        section = get_parent_of_type(storey, "IfcSpatialStructureElement") if storey else None
        section_clean = strip_prefix(section.ObjectType, "BRU_Секция_") if section and section.ObjectType else ""

        rows.append([
            flat_type,
            flat_number,
            area,
            storey_name,
            floor_num,
            section_clean
        ])

    # сортировка
    sort_rows_by_flat_number(rows)

    # записываем CSV
    if os.path.isfile(csv_path):
        os.remove(csv_path)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)

    print(f"OK ({len(rows)} квартир, {os.path.basename(csv_path)})")


# ------------------------------------------------------------
# точка входа
# ------------------------------------------------------------
def main():
    # пути, заданные пользователем
    paths = sys.argv[1:]

    # если не указаны – ищем *.ifc *.ifczip рядом со скриптом
    if not paths:
        script_dir = os.path.dirname(os.path.realpath(__file__)) or "."
        paths = sorted(
            glob.glob(os.path.join(script_dir, "*.ifc")) +
            glob.glob(os.path.join(script_dir, "*.ifczip"))
        )
        if not paths:
            print("Файлы *.ifc / *.ifczip не найдены.")
            return

    for ifc_path in paths:
        if not os.path.isfile(ifc_path):
            print(f"! Файл не найден: {ifc_path}")
            continue
        name_no_ext = os.path.splitext(ifc_path)[0]
        csv_path = name_no_ext + ".csv"
        export_flats(ifc_path, csv_path)


if __name__ == "__main__":
    main()