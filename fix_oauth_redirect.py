#!/usr/bin/env python3
"""
Диагностика и исправление проблемы redirect_uri_mismatch
"""

import os
import json
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import sys

# Загружаем переменные окружения
load_dotenv()


def diagnose_redirect_uri():
    """Диагностика проблемы с redirect_uri"""

    print("=" * 60)
    print("🔍 ДИАГНОСТИКА REDIRECT_URI_MISMATCH")
    print("=" * 60)

    # 1. Проверяем переменные окружения
    print("\n1️⃣ Проверка переменных окружения:")

    client_id = os.getenv('GOOGLE_CLIENT_ID')
    ngrok_url = os.getenv('NGROK_URL')

    print(f"   GOOGLE_CLIENT_ID: {client_id[:30]}..." if client_id else "   ❌ GOOGLE_CLIENT_ID не установлен")
    print(f"   NGROK_URL: {ngrok_url}" if ngrok_url else "   ❌ NGROK_URL не установлен")

    # 2. Проверяем текущий ngrok туннель
    print("\n2️⃣ Проверка активного ngrok туннеля:")

    actual_ngrok_url = None
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        data = response.json()
        if data.get('tunnels'):
            actual_ngrok_url = data['tunnels'][0]['public_url']
            print(f"   ✅ Активный туннель: {actual_ngrok_url}")

            if ngrok_url != actual_ngrok_url:
                print(f"   ⚠️  НЕ СОВПАДАЕТ с NGROK_URL в .env!")
                print(f"   📝 Нужно обновить .env")
        else:
            print("   ❌ Нет активных туннелей")
    except:
        print("   ❌ ngrok не запущен или не отвечает")

    # 3. Определяем правильные redirect_uri
    print("\n3️⃣ Необходимые redirect_uri для Google Console:")

    if actual_ngrok_url:
        print(f"\n   Для ngrok:")
        print(f"   • {actual_ngrok_url}/auth/callback")

    print(f"\n   Для локальной разработки:")
    print(f"   • http://localhost:5001/auth/callback")
    print(f"   • http://127.0.0.1:5001/auth/callback")

    # 4. Проверяем, что Flask использует
    print("\n4️⃣ Проверка Flask конфигурации:")

    try:
        # Делаем запрос на /login чтобы увидеть redirect
        response = requests.get('http://localhost:5001/login',
                                allow_redirects=False,
                                timeout=5)

        if response.status_code == 302:
            location = response.headers.get('Location', '')

            # Парсим URL чтобы найти redirect_uri
            if 'accounts.google.com' in location:
                parsed = urlparse(location)
                params = parse_qs(parsed.query)

                redirect_uri = params.get('redirect_uri', [''])[0]

                print(f"   Flask использует redirect_uri: {redirect_uri}")

                if actual_ngrok_url and actual_ngrok_url not in redirect_uri:
                    print(f"   ⚠️  Flask не использует ngrok URL!")
                    print(f"   📝 Проблема в auth_system.py")
            else:
                print(f"   ⚠️  Redirect не на Google OAuth")
        else:
            print(f"   ❌ /login вернул статус {response.status_code}")

    except Exception as e:
        print(f"   ❌ Ошибка при проверке Flask: {e}")

    # 5. Инструкции по исправлению
    print("\n" + "=" * 60)
    print("📋 ИНСТРУКЦИИ ПО ИСПРАВЛЕНИЮ")
    print("=" * 60)

    if actual_ngrok_url:
        print(f"\n✅ ШАГ 1: Обновите .env файл:")
        print(f"   NGROK_URL={actual_ngrok_url}")

        print(f"\n✅ ШАГ 2: Добавьте в Google Console:")
        print(f"   https://console.cloud.google.com/apis/credentials")
        print(f"\n   Authorized redirect URIs:")
        print(f"   • {actual_ngrok_url}/auth/callback")
        print(f"   • http://localhost:5001/auth/callback")
        print(f"   • http://127.0.0.1:5001/auth/callback")

        print(f"\n✅ ШАГ 3: Перезапустите Flask приложение")

        # Предложение автоматического исправления
        print("\n" + "=" * 60)
        if input("🔧 Автоматически обновить .env файл? (y/n): ").lower() == 'y':
            update_env_file(actual_ngrok_url)
            print("✅ .env обновлен!")
            print("📝 Не забудьте обновить Google Console и перезапустить Flask!")
    else:
        print("\n❌ Сначала запустите ngrok:")
        print("   ngrok http 5001")
        print("\n   Затем запустите этот скрипт снова")


def update_env_file(ngrok_url):
    """Обновление .env файла с правильным URL"""

    # Читаем текущий .env
    env_lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_lines = f.readlines()

    # Обновляем или добавляем NGROK_URL
    ngrok_found = False
    for i, line in enumerate(env_lines):
        if line.startswith('NGROK_URL='):
            env_lines[i] = f'NGROK_URL={ngrok_url}\n'
            ngrok_found = True
            break

    if not ngrok_found:
        env_lines.append(f'NGROK_URL={ngrok_url}\n')

    # Записываем обратно
    with open('.env', 'w') as f:
        f.writelines(env_lines)

    print(f"✅ Обновлен NGROK_URL в .env: {ngrok_url}")


def check_google_console_urls():
    """Генерация списка всех возможных redirect_uri для копирования"""

    print("\n" + "=" * 60)
    print("📋 ПОЛНЫЙ СПИСОК URL ДЛЯ GOOGLE CONSOLE")
    print("=" * 60)

    # Получаем текущий ngrok URL
    ngrok_url = None
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        data = response.json()
        if data.get('tunnels'):
            ngrok_url = data['tunnels'][0]['public_url']
    except:
        pass

    print("\n🔗 Authorized JavaScript origins:")
    print("   (скопируйте все строки)")
    print()

    if ngrok_url:
        print(f"{ngrok_url}")
    print("http://localhost:5001")
    print("http://localhost")
    print("http://127.0.0.1:5001")
    print("http://127.0.0.1")

    print("\n🔗 Authorized redirect URIs:")
    print("   (скопируйте все строки)")
    print()

    if ngrok_url:
        print(f"{ngrok_url}/auth/callback")
    print("http://localhost:5001/auth/callback")
    print("http://localhost/auth/callback")
    print("http://127.0.0.1:5001/auth/callback")
    print("http://127.0.0.1/auth/callback")

    print("\n📝 Скопируйте ВСЕ URL в Google Console для избежания ошибок")
    print("   Лишние URL не помешают, а отсутствующие вызовут ошибку")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--urls':
        check_google_console_urls()
    else:
        diagnose_redirect_uri()
        print("\n💡 Подсказка: запустите с --urls для получения полного списка URL")
        print("   python3 fix_oauth_redirect.py --urls")