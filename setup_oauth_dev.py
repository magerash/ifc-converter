#!/usr/bin/env python3
"""
Автоматическая настройка OAuth2 для разработки с ngrok
"""

import os
import json
import time
import subprocess
import requests
from dotenv import load_dotenv, set_key

def get_ngrok_url():
    """Получение публичного URL от ngrok"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        data = response.json()
        if data['tunnels']:
            return data['tunnels'][0]['public_url']
    except:
        return None

def start_ngrok():
    """Запуск ngrok в фоне"""
    print("🔧 Запускаем ngrok...")
    # subprocess.Popen(['ngrok', 'http', '5000'],
    subprocess.Popen(['ngrok', 'http', '5001'],  # ======================= ВТОРОЙ СЕРВЕР ======================= #
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    time.sleep(3)

def update_env_file(ngrok_url):
    """Обновление .env файла"""
    env_path = '.env'

    # Создаем файл если не существует
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write('# OAuth2 Configuration\n')

    # Обновляем URL
    set_key(env_path, 'NGROK_URL', ngrok_url)
    print(f"✅ Обновлен .env файл с URL: {ngrok_url}")

def print_instructions(ngrok_url):
    """Вывод инструкций для пользователя"""
    print("\n" + "="*60)
    print("📋 ИНСТРУКЦИИ ПО НАСТРОЙКЕ GOOGLE OAUTH2")
    print("="*60)
    print("\n1. Перейдите в Google Cloud Console:")
    print("   https://console.cloud.google.com/apis/credentials\n")
    print("2. Выберите ваш OAuth 2.0 Client ID\n")
    print("3. Добавьте следующие URLs:\n")
    print("   Authorized JavaScript origins:")
    print(f"   ✅ {ngrok_url}")
    print("\n   Authorized redirect URIs:")
    print(f"   ✅ {ngrok_url}/auth/callback")
    print("\n4. Сохраните изменения и подождите 5 минут")
    print("\n" + "="*60)

def test_oauth_flow(ngrok_url):
    """Тестирование OAuth2 flow"""
    print("\n🧪 Тестирование OAuth2...")

    # Проверяем доступность
    try:
        response = requests.get(f"{ngrok_url}/health")
        if response.status_code == 200:
            print("✅ Приложение доступно")
        else:
            print(f"⚠️ Приложение вернуло статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return

    # Проверяем login endpoint
    login_url = f"{ngrok_url}/login"
    print(f"\n🔗 URL для тестирования входа:")
    print(f"   {login_url}")

    # Открываем в браузере
    import webbrowser
    if input("\nОткрыть в браузере? (y/n): ").lower() == 'y':
        webbrowser.open(login_url)

def main():
    print("🚀 Настройка OAuth2 для разработки с ngrok")
    print("="*60)

    # Загружаем существующие переменные
    load_dotenv()

    # Проверяем наличие OAuth credentials
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("⚠️ Не найдены GOOGLE_CLIENT_ID или GOOGLE_CLIENT_SECRET в .env")
        print("Добавьте их перед продолжением.")
        return

    # Запускаем ngrok
    start_ngrok()

    # Получаем URL
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print("❌ Не удалось получить ngrok URL")
        return

    print(f"✅ ngrok URL: {ngrok_url}")

    # Обновляем .env
    update_env_file(ngrok_url)

    # Показываем инструкции
    print_instructions(ngrok_url)

    # Ждем подтверждения
    input("\nНажмите Enter после обновления настроек в Google Console...")

    # Тестируем
    test_oauth_flow(ngrok_url)

    print("\n✅ Настройка завершена!")
    print(f"Приложение доступно по адресу: {ngrok_url}")

if __name__ == "__main__":
    main()
