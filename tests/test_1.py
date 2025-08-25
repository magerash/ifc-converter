#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования новых функций IFC Converter 2.0
"""

import os
import requests
import time
import tempfile
from file_naming_utils import get_next_indexed_filename, get_unique_sheet_name, sanitize_sheet_name


def test_file_naming():
    """Тестирование системы именования файлов"""
    print("🔧 Тестирование системы именования файлов...")

    # Создаем временную директорию для тестов
    with tempfile.TemporaryDirectory() as temp_dir:
        # Тест 1: Обычное имя файла
        result1 = get_next_indexed_filename(temp_dir, "test.csv")
        print(f"✅ Обычное имя: test.csv → {result1}")

        # Создаем файл для тестирования дублирования
        test_file = os.path.join(temp_dir, "test.csv")
        with open(test_file, 'w') as f:
            f.write("test")

        # Тест 2: Дублирование имени
        result2 = get_next_indexed_filename(temp_dir, "test.csv")
        print(f"✅ Дублирование: test.csv → {result2}")

        # Создаем еще один файл
        test_file2 = os.path.join(temp_dir, result2)
        with open(test_file2, 'w') as f:
            f.write("test")

        # Тест 3: Множественное дублирование
        result3 = get_next_indexed_filename(temp_dir, "test.csv")
        print(f"✅ Множественное дублирование: test.csv → {result3}")

        # Тест 4: Имя с недопустимыми символами
        result4 = get_next_indexed_filename(temp_dir, "test<>file:name.csv")
        print(f"✅ Недопустимые символы: test<>file:name.csv → {result4}")

        print("✅ Тестирование именования файлов завершено\n")


def test_sheet_naming():
    """Тестирование именования листов Google Sheets"""
    print("📊 Тестирование именования листов Google Sheets...")

    # Мокаем объект spreadsheet
    class MockWorksheet:
        def __init__(self, title):
            self.title = title

    class MockSpreadsheet:
        def __init__(self):
            self.worksheets_list = [
                MockWorksheet("Sheet1"),
                MockWorksheet("Project_Model"),
                MockWorksheet("Project_Model_1"),
                MockWorksheet("Test_Sheet")
            ]

        def worksheets(self):
            return self.worksheets_list

    mock_spreadsheet = MockSpreadsheet()

    # Тест 1: Уникальное имя
    result1 = get_unique_sheet_name(mock_spreadsheet, "New_Project.ifc")
    print(f"✅ Уникальное имя: New_Project.ifc → {result1}")

    # Тест 2: Дублирование
    result2 = get_unique_sheet_name(mock_spreadsheet, "Project_Model.ifc")
    print(f"✅ Дублирование: Project_Model.ifc → {result2}")

    # Тест 3: Множественное дублирование
    result3 = get_unique_sheet_name(mock_spreadsheet, "Project_Model.ifc")
    print(f"✅ Множественное дублирование: Project_Model.ifc → {result3}")

    # Тест 4: Очистка имени
    result4 = sanitize_sheet_name("Test@#$%^&*()File.ifc")
    print(f"✅ Очистка символов: Test@#$%^&*()File.ifc → {result4}")

    print("✅ Тестирование именования листов завершено\n")


def test_health_check(base_url="http://localhost:5000"):
    """Тестирование health check endpoints"""
    print("💚 Тестирование Health Check...")

    try:
        # Тест JSON endpoint
        response = requests.get(f"{base_url}/health?format=json", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ JSON Health Check: {data['status']}")
            print(f"   Версия: {data.get('version', 'неизвестна')}")
            print(f"   Время работы: {data.get('uptime', 'неизвестно')}")
        else:
            print(f"❌ JSON Health Check failed: {response.status_code}")

        # Тест HTML endpoint
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ HTML Health Check: OK")
        else:
            print(f"❌ HTML Health Check failed: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Health Check недоступен: {e}")
        print("   Убедитесь, что приложение запущено на localhost:5000")

    print("✅ Тестирование Health Check завершено\n")


def test_api_endpoints(base_url="http://localhost:5000"):
    """Тестирование API endpoints"""
    print("🌐 Тестирование API endpoints...")

    endpoints = [
        ("/", "GET", "Главная страница"),
        ("/health", "GET", "Health Check HTML"),
        ("/health?format=json", "GET", "Health Check JSON"),
        ("/login", "GET", "Страница авторизации"),
    ]

    for endpoint, method, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅" if response.status_code in [200, 302] else "❌"
            print(f"{status} {method} {endpoint} ({description}): {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {method} {endpoint} ({description}): Ошибка - {e}")

    print("✅ Тестирование API endpoints завершено\n")


def test_file_upload_simulation():
    """Симуляция загрузки файла (без реального файла)"""
    print("📤 Тестирование загрузки файлов...")

    # Создаем тестовый IFC файл (минимальный)
    test_ifc_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition[CoordinationView]'),'2;1');
FILE_NAME('test.ifc','2025-08-24T12:00:00',('Test'),('Test'),'IfcOpenShell','IfcOpenShell','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('0YvhMod9X3uvUyOaWNb6oP',$,'Test Project',$,$,$,$,$,#2);
#2=IFCUNITASSIGNMENT((#3));
#3=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
ENDSEC;
END-ISO-10303-21;"""

    try:
        with tempfile.NamedTemporaryFile(suffix='.ifc', mode='w', delete=False) as f:
            f.write(test_ifc_content)
            temp_ifc_path = f.name

        print(f"✅ Создан тестовый IFC файл: {os.path.basename(temp_ifc_path)}")

        # Здесь можно было бы протестировать реальную загрузку,
        # но это требует запущенного сервера
        print("💡 Для полного тестирования загрузки запустите сервер и используйте:")
        print("   curl -F 'file=@test.ifc' http://localhost:5000/uploads")

        # Очищаем временный файл
        os.unlink(temp_ifc_path)

    except Exception as e:
        print(f"❌ Ошибка создания тестового файла: {e}")

    print("✅ Тестирование загрузки файлов завершено\n")


def check_environment():
    """Проверка переменных окружения"""
    print("🔍 Проверка переменных окружения...")

    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GS_SPREADSHEET_ID',
        'GS_CLIENT_EMAIL',
        'SECRET_KEY'
    ]

    missing = []
    present = []

    for var in required_vars:
        if os.getenv(var):
            present.append(var)
            # Показываем только начало значения для безопасности
            value = os.getenv(var)
            display = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {var}: {display}")
        else:
            missing.append(var)
            print(f"❌ {var}: НЕ УСТАНОВЛЕНА")

    print(f"\n📊 Результат: {len(present)}/{len(required_vars)} переменных установлено")

    if missing:
        print("⚠️ Для полной функциональности установите недостающие переменные")
        print("   Смотрите .env.example для примера")
    else:
        print("🎉 Все основные переменные настроены!")

    print("✅ Проверка окружения завершена\n")


def main():
    """Главная функция тестирования"""
    print("🧪 IFC Converter 2.0 - Комплексное тестирование")
    print("=" * 50)

    # Тестируем функции именования (не требуют сервера)
    test_file_naming()
    test_sheet_naming()

    # Проверяем переменные окружения
    check_environment()

    # Тестируем API (требует запущенного сервера)
    print("⚠️ Следующие тесты требуют запущенного сервера...")
    time.sleep(2)

    test_health_check()
    test_api_endpoints()
    test_file_upload_simulation()

    print("=" * 50)
    print("🎯 Тестирование завершено!")
    print("\n📋 Следующие шаги:")
    print("1. Убедитесь, что все переменные окружения настроены")
    print("2. Запустите сервер: docker-compose up -d")
    print("3. Проверьте health check: http://localhost:5000/health")
    print("4. Протестируйте авторизацию и загрузку файлов")


if __name__ == "__main__":
    main()