#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностический скрипт для проверки настройки Google Sheets API
Уже в вертке master
"""

import os
import sys
from gsheets import validate_gs_credentials, upload_to_google_sheets
import logging

# Настройка логгера для диагностики
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('gs-diagnostic')


def check_environment_variables():
    """Проверка переменных окружения"""
    print("=" * 50)
    print("ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("=" * 50)

    required_vars = [
        'GS_TYPE', 'GS_PROJECT_ID', 'GS_PRIVATE_KEY_ID', 'GS_PRIVATE_KEY',
        'GS_CLIENT_EMAIL', 'GS_CLIENT_ID', 'GS_AUTH_URI', 'GS_TOKEN_URI',
        'GS_SPREADSHEET_ID'
    ]

    missing = []
    present = []

    for var in required_vars:
        value = os.getenv(var)
        if value:
            present.append(var)
            # Показываем только начало значения для безопасности
            if 'KEY' in var or 'ID' in var:
                display_value = value[:10] + "..." if len(value) > 10 else value
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            missing.append(var)
            print(f"❌ {var}: НЕ УСТАНОВЛЕНА")

    print(f"\nРезультат: {len(present)}/{len(required_vars)} переменных установлено")

    if missing:
        print(f"\n⚠️ Отсутствуют переменные: {', '.join(missing)}")
        return False

    # Проверка placeholder значений
    project_id = os.getenv('GS_PROJECT_ID', '')
    if project_id.startswith('your-'):
        print("\n⚠️ Обнаружены placeholder значения в переменных окружения")
        print("Замените значения в .env файле на реальные данные от Google API")
        return False

    print("\n✅ Все переменные окружения настроены корректно")
    return True


def test_credentials_validation():
    """Тест валидации учетных данных"""
    print("\n" + "=" * 50)
    print("ПРОВЕРКА ВАЛИДАЦИИ УЧЕТНЫХ ДАННЫХ")
    print("=" * 50)

    try:
        validate_gs_credentials()
        print("✅ Валидация учетных данных прошла успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка валидации: {str(e)}")
        return False


def test_google_sheets_connection():
    """Тест подключения к Google Sheets"""
    print("\n" + "=" * 50)
    print("ТЕСТ ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS")
    print("=" * 50)

    # Создаем тестовый CSV файл
    import tempfile
    import csv

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['FlatType', 'Area_m2', 'Section', 'FloorNum', 'StoreyName', 'FlatNumber'])
            writer.writerow(['1С', '45,5', '1', '1', 'Этаж 1', '1'])
            writer.writerow(['2С', '62,3', '1', '1', 'Этаж 1', '2'])
            test_csv_path = f.name

        print(f"📄 Создан тестовый CSV файл: {test_csv_path}")

        # Пытаемся загрузить в Google Sheets
        print("🔄 Попытка загрузки в Google Sheets...")
        sheet_url = upload_to_google_sheets(test_csv_path, "diagnostic_test.ifc")

        if sheet_url:
            print(f"✅ Успешная загрузка в Google Sheets!")
            print(f"🔗 URL таблицы: {sheet_url}")
            return True
        else:
            print("❌ Загрузка не удалась - получен пустой URL")
            return False

    except Exception as e:
        print(f"❌ Ошибка при тестировании подключения: {str(e)}")
        print(f"📋 Тип ошибки: {type(e).__name__}")

        # Дополнительная диагностика для разных типов ошибок
        error_str = str(e).lower()

        if "permission" in error_str or "forbidden" in error_str:
            print("\n💡 Рекомендации:")
            print("   1. Проверьте права доступа сервисного аккаунта к таблице")
            print("   2. Убедитесь, что таблица расшарена для email сервисного аккаунта")
            print(f"   3. Email сервисного аккаунта: {os.getenv('GS_CLIENT_EMAIL', 'НЕ УСТАНОВЛЕН')}")

        elif "not found" in error_str:
            print("\n💡 Рекомендации:")
            print("   1. Проверьте корректность GS_SPREADSHEET_ID")
            print("   2. Убедитесь, что таблица существует")
            print(f"   3. Текущий ID таблицы: {os.getenv('GS_SPREADSHEET_ID', 'НЕ УСТАНОВЛЕН')}")

        elif "credential" in error_str or "auth" in error_str:
            print("\n💡 Рекомендации:")
            print("   1. Проверьте корректность JSON ключа сервисного аккаунта")
            print("   2. Убедитесь, что приватный ключ не содержит лишних символов")
            print("   3. Проверьте, что сервисный аккаунт активен в Google Cloud")

        return False

    finally:
        # Удаляем тестовый файл
        try:
            if 'test_csv_path' in locals():
                os.unlink(test_csv_path)
                print(f"🗑️ Удален тестовый файл: {test_csv_path}")
        except Exception:
            pass


def check_dotenv_file():
    """Проверка наличия и содержимого .env файла"""
    print("\n" + "=" * 50)
    print("ПРОВЕРКА .ENV ФАЙЛА")
    print("=" * 50)

    env_path = '../.env'
    if os.path.exists(env_path):
        print(f"✅ Файл .env найден: {os.path.abspath(env_path)}")

        # Читаем файл и показываем структуру (без значений)
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            print(f"📄 Содержит {len(lines)} строк")

            vars_in_file = []
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    var_name = line.split('=')[0].strip()
                    vars_in_file.append(var_name)
                    print(f"   {line_num}: {var_name}=...")
                elif line.startswith('#'):
                    print(f"   {line_num}: # комментарий")
                elif line:
                    print(f"   {line_num}: {line}")

            print(f"\n📊 Найдено {len(vars_in_file)} переменных в файле")
            return True

        except Exception as e:
            print(f"❌ Ошибка чтения .env файла: {str(e)}")
            return False
    else:
        print(f"❌ Файл .env не найден в: {os.path.abspath('..')}")
        print("\n💡 Создайте файл .env с переменными Google Sheets API")
        return False


def main():
    """Главная функция диагностики"""
    print("🔍 ДИАГНОСТИКА GOOGLE SHEETS API")
    print("=" * 60)

    results = {
        'env_file': check_dotenv_file(),
        'env_vars': check_environment_variables(),
        'validation': test_credentials_validation(),
        'connection': False
    }

    # Тест подключения только если предыдущие проверки прошли
    if results['env_vars'] and results['validation']:
        results['connection'] = test_google_sheets_connection()
    else:
        print("\n⏭️ Пропуск теста подключения из-за ошибок конфигурации")

    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)

    tests = [
        ('Файл .env', results['env_file']),
        ('Переменные окружения', results['env_vars']),
        ('Валидация учетных данных', results['validation']),
        ('Подключение к Google Sheets', results['connection'])
    ]

    for test_name, test_result in tests:
        status = "✅ ПРОЙДЕН" if test_result else "❌ ПРОВАЛЕН"
        print(f"{test_name:<30} {status}")

    passed_tests = sum(results.values())
    total_tests = len(results)

    print(f"\nОбщий результат: {passed_tests}/{total_tests} тестов пройдено")

    if passed_tests == total_tests:
        print("🎉 Все проверки пройдены! Google Sheets API настроен корректно.")
    else:
        print("⚠️ Обнаружены проблемы с конфигурацией Google Sheets API.")
        print("\n📝 Рекомендуемые действия:")
        print("1. Проверьте настройки в .env файле")
        print("2. Убедитесь, что сервисный аккаунт имеет доступ к таблице")
        print("3. Проверьте правильность GS_SPREADSHEET_ID")
        print("4. Убедитесь, что Google Sheets API включен в проекте")


if __name__ == "__main__":
    main()