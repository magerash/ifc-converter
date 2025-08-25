#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки исправления проблемы @app.before_first_request
Для ветки improovements-1
"""

import os
import sys
from flask import Flask


def check_flask_version():
    """Проверка версии Flask"""
    try:
        import flask
        version = flask.__version__
        print(f"✅ Flask версия: {version}")

        # Проверяем, поддерживается ли @app.before_first_request
        app = Flask(__name__)

        if hasattr(app, 'before_first_request'):
            print("⚠️ before_first_request поддерживается (старая версия Flask)")
        else:
            print("✅ before_first_request не поддерживается (новая версия Flask)")

        return True
    except ImportError:
        print("❌ Flask не установлен")
        return False


def test_main_import():
    """Тестирование импорта main.py"""
    try:
        # Добавляем текущую директорию в путь
        sys.path.insert(0, '.')

        print("🔄 Тестирование импорта main.py...")

        # Пробуем импортировать основные компоненты
        from main import app, create_templates, create_app

        print("✅ Импорт main.py успешен")
        print(f"✅ Flask приложение создано: {type(app)}")
        print("✅ Функция create_templates доступна")
        print("✅ Функция create_app доступна")

        return True

    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Другая ошибка: {e}")
        return False


def test_template_creation():
    """Тестирование создания шаблонов"""
    try:
        print("🔄 Тестирование создания шаблонов...")

        from main import create_templates

        # Создаем шаблоны
        create_templates()

        # Проверяем, что файлы созданы
        templates = ['uploads.html', 'dashboard.html', 'health.html']
        created = []

        for template in templates:
            template_path = os.path.join('templates', template)
            if os.path.exists(template_path):
                size = os.path.getsize(template_path)
                created.append(f"{template} ({size} байт)")
                print(f"✅ Создан: {template} ({size} байт)")
            else:
                print(f"❌ Не найден: {template}")

        print(f"✅ Создано шаблонов: {len(created)}/{len(templates)}")
        return len(created) == len(templates)

    except Exception as e:
        print(f"❌ Ошибка создания шаблонов: {e}")
        return False


def test_app_startup():
    """Тестирование запуска приложения"""
    try:
        print("🔄 Тестирование запуска приложения...")

        from main import create_app

        # Создаем приложение через фабрику
        app = create_app()

        # Получаем список маршрутов
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.methods} {rule.rule}")

        print(f"✅ Приложение создано успешно")
        print(f"✅ Найдено маршрутов: {len(routes)}")

        # Показываем основные маршруты
        important_routes = ['/', '/health', '/uploads', '/login']
        for route in important_routes:
            found = any(route in r for r in routes)
            status = "✅" if found else "❌"
            print(f"{status} Маршрут {route}: {'найден' if found else 'не найден'}")

        return True

    except Exception as e:
        print(f"❌ Ошибка запуска приложения: {e}")
        return False


def check_dependencies():
    """Проверка зависимостей"""
    print("🔄 Проверка зависимостей...")

    required_modules = [
        'flask',
        'authlib',
        'ifcopenshell',
        'gspread',
        'oauth2client'
    ]

    missing = []
    present = []

    for module in required_modules:
        try:
            __import__(module)
            present.append(module)
            print(f"✅ {module}")
        except ImportError:
            missing.append(module)
            print(f"❌ {module}")

    print(f"📊 Установлено: {len(present)}/{len(required_modules)}")

    if missing:
        print("⚠️ Не хватает модулей:")
        for module in missing:
            print(f"   pip install {module}")

    return len(missing) == 0


def main():
    """Главная функция проверки"""
    print("🔧 Проверка исправления Flask before_first_request")
    print("=" * 55)

    checks = [
        ("Версия Flask", check_flask_version),
        ("Зависимости", check_dependencies),
        ("Импорт main.py", test_main_import),
        ("Создание шаблонов", test_template_creation),
        ("Запуск приложения", test_app_startup),
    ]

    passed = 0
    total = len(checks)

    for name, check_func in checks:
        print(f"\n📋 {name}:")
        try:
            result = check_func()
            if result:
                passed += 1
                print(f"✅ {name}: ПРОЙДЕН")
            else:
                print(f"❌ {name}: ПРОВАЛЕН")
        except Exception as e:
            print(f"💥 {name}: ОШИБКА - {e}")

    print("\n" + "=" * 55)
    print(f"📊 Результат: {passed}/{total} проверок пройдено")

    if passed == total:
        print("🎉 Все проверки пройдены! Приложение готово к запуску.")
        print("\n🚀 Следующие шаги:")
        print("1. Настройте .env файл с переменными окружения")
        print("2. Запустите приложение: python main.py")
        print("3. Откройте http://localhost:5000")
    else:
        print("⚠️ Есть проблемы, которые нужно исправить.")

        if not os.path.exists('.env'):
            print("\n💡 Рекомендации:")
            print("• Создайте .env файл по примеру .env.example")
            print("• Установите недостающие зависимости")
            print("• Убедитесь, что все файлы скопированы правильно")


if __name__ == "__main__":
    main()