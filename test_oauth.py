#!/usr/bin/env python3
"""
Скрипт для тестирования OAuth2 настройки с ngrok
Проверяет все компоненты системы авторизации
"""

import os
import sys
import json
import time
import requests
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Инициализация colorama для цветного вывода
init(autoreset=True)

# Загружаем переменные окружения
load_dotenv()


class OAuth2Tester:
    """Класс для тестирования OAuth2 конфигурации"""

    def __init__(self):
        self.ngrok_url = None
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.errors = []
        self.warnings = []

    def print_header(self, text):
        """Печать заголовка"""
        print(f"\n{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.CYAN}{text}")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")

    def print_success(self, text):
        """Печать успешного результата"""
        print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

    def print_error(self, text):
        """Печать ошибки"""
        print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")
        self.errors.append(text)

    def print_warning(self, text):
        """Печать предупреждения"""
        print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")
        self.warnings.append(text)

    def print_info(self, text):
        """Печать информации"""
        print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")

    def check_environment(self):
        """Проверка переменных окружения"""
        self.print_header("ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")

        required_vars = {
            'GOOGLE_CLIENT_ID': self.client_id,
            'GOOGLE_CLIENT_SECRET': self.client_secret,
            'SECRET_KEY': os.getenv('SECRET_KEY')
        }

        for var_name, var_value in required_vars.items():
            if var_value:
                if var_name == 'GOOGLE_CLIENT_SECRET':
                    display_value = var_value[:10] + "..." if len(var_value) > 10 else var_value
                else:
                    display_value = var_value[:30] + "..." if len(var_value) > 30 else var_value
                self.print_success(f"{var_name}: {display_value}")
            else:
                self.print_error(f"{var_name}: НЕ УСТАНОВЛЕНА")

        # Проверка OAuth2 конфигурации
        if self.client_id and '.apps.googleusercontent.com' in self.client_id:
            self.print_success("Client ID имеет правильный формат")
        elif self.client_id:
            self.print_warning("Client ID может иметь неправильный формат")

        return len(self.errors) == 0

    def check_ngrok(self):
        """Проверка ngrok"""
        self.print_header("ПРОВЕРКА NGROK")

        # Проверка установки ngrok
        try:
            result = subprocess.run(['ngrok', 'version'],
                                    capture_output=True,
                                    text=True,
                                    timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_success(f"ngrok установлен: {version}")
            else:
                self.print_error("ngrok установлен, но не работает корректно")
                return False
        except FileNotFoundError:
            self.print_error("ngrok не установлен")
            self.print_info("Установите с https://ngrok.com/download")
            return False
        except subprocess.TimeoutExpired:
            self.print_error("ngrok не отвечает")
            return False

        # Проверка запущенного туннеля
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
            data = response.json()

            if data.get('tunnels'):
                tunnel = data['tunnels'][0]
                self.ngrok_url = tunnel['public_url']
                self.print_success(f"ngrok туннель активен: {self.ngrok_url}")

                # Сохраняем в переменные окружения
                os.environ['NGROK_URL'] = self.ngrok_url

                # Проверка метрик туннеля
                metrics = tunnel.get('metrics', {})
                if metrics:
                    conns = metrics.get('conns', {})
                    self.print_info(f"Соединений: {conns.get('count', 0)}")
            else:
                self.print_warning("ngrok запущен, но туннель не найден")
                self.print_info("Запустите: ngrok http 5001")
                return False

        except requests.exceptions.RequestException:
            self.print_warning("ngrok не запущен или не отвечает")
            self.print_info("Запустите: ngrok http 5001")
            return False

        return True

    def check_flask_app(self):
        """Проверка Flask приложения"""
        self.print_header("ПРОВЕРКА FLASK ПРИЛОЖЕНИЯ")

        # Проверяем локальный Flask
        try:
            response = requests.get('http://localhost:5001/health', timeout=5)
            if response.status_code == 200:
                self.print_success("Flask приложение запущено локально")

                # Проверяем JSON endpoint
                response_json = requests.get('http://localhost:5001/health?format=json', timeout=5)
                if response_json.status_code == 200:
                    data = response_json.json()
                    self.print_info(f"Версия: {data.get('version', 'неизвестна')}")
                    self.print_info(f"Статус: {data.get('status', 'неизвестен')}")
            else:
                self.print_error(f"Flask отвечает с кодом: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            self.print_error("Flask приложение не запущено на порту 5001")
            self.print_info("Запустите: python main.py")
            return False

        # Проверяем через ngrok
        if self.ngrok_url:
            try:
                # ngrok может требовать обход предупреждения
                headers = {'ngrok-skip-browser-warning': 'true'}
                response = requests.get(f"{self.ngrok_url}/health",
                                        headers=headers,
                                        timeout=10)
                if response.status_code == 200:
                    self.print_success(f"Flask доступен через ngrok: {self.ngrok_url}")
                else:
                    self.print_warning(f"Flask через ngrok вернул код: {response.status_code}")

            except requests.exceptions.RequestException as e:
                self.print_warning(f"Не удалось подключиться через ngrok: {str(e)}")

        return True

    def check_oauth_endpoints(self):
        """Проверка OAuth2 endpoints"""
        self.print_header("ПРОВЕРКА OAUTH2 ENDPOINTS")

        if not self.ngrok_url:
            self.print_warning("ngrok URL не доступен, пропускаем проверку")
            return False

        endpoints = [
            ('/', 'Главная страница'),
            ('/login', 'Login endpoint'),
            ('/auth/callback', 'OAuth callback'),
            ('/dashboard', 'Dashboard (требует авторизацию)')
        ]

        headers = {'ngrok-skip-browser-warning': 'true'}

        for endpoint, description in endpoints:
            url = f"{self.ngrok_url}{endpoint}"
            try:
                response = requests.get(url,
                                        headers=headers,
                                        timeout=10,
                                        allow_redirects=False)

                if response.status_code in [200, 302, 303]:
                    self.print_success(f"{description}: {response.status_code}")

                    # Для login endpoint проверяем redirect на Google
                    if endpoint == '/login' and response.status_code in [302, 303]:
                        location = response.headers.get('Location', '')
                        if 'accounts.google.com' in location:
                            self.print_success("Redirect на Google OAuth работает")
                        else:
                            self.print_warning("Redirect не ведет на Google")

                elif response.status_code == 401:
                    self.print_info(f"{description}: требует авторизацию (401)")
                else:
                    self.print_warning(f"{description}: код {response.status_code}")

            except requests.exceptions.RequestException as e:
                self.print_error(f"{description}: ошибка подключения")

        return True

    def check_google_console_config(self):
        """Инструкции по проверке Google Console"""
        self.print_header("ПРОВЕРКА GOOGLE CONSOLE CONFIGURATION")

        if not self.ngrok_url:
            self.print_warning("ngrok URL не доступен")
            return

        print(f"\n{Fore.YELLOW}Проверьте настройки в Google Console:")
        print(f"{Fore.WHITE}1. Перейдите: https://console.cloud.google.com/apis/credentials")
        print(f"{Fore.WHITE}2. Выберите ваш OAuth 1.1 Client ID")
        print(f"{Fore.WHITE}3. Убедитесь что добавлены:")
        print(f"\n   {Fore.GREEN}Authorized JavaScript origins:")
        print(f"   {Fore.CYAN}• {self.ngrok_url}")
        print(f"   {Fore.CYAN}• http://localhost:5001")
        print(f"\n   {Fore.GREEN}Authorized redirect URIs:")
        print(f"   {Fore.CYAN}• {self.ngrok_url}/auth/callback")
        print(f"   {Fore.CYAN}• http://localhost:5001/auth/callback")

        print(f"\n{Fore.YELLOW}Текущий Client ID: {Fore.CYAN}{self.client_id[:30]}...")

    def simulate_oauth_flow(self):
        """Симуляция OAuth2 flow"""
        self.print_header("СИМУЛЯЦИЯ OAUTH2 FLOW")

        if not self.ngrok_url:
            self.print_error("Требуется активный ngrok туннель")
            return False

        print(f"\n{Fore.CYAN}Тестовые URL для проверки:")
        print(f"{Fore.WHITE}1. Вход через браузер:")
        print(f"   {Fore.GREEN}{self.ngrok_url}/login")

        print(f"\n{Fore.WHITE}2. Прямая проверка callback:")
        print(f"   {Fore.GREEN}{self.ngrok_url}/auth/callback")

        print(f"\n{Fore.WHITE}3. Dashboard (после входа):")
        print(f"   {Fore.GREEN}{self.ngrok_url}/dashboard")

        # Опционально открываем в браузере
        if input(f"\n{Fore.YELLOW}Открыть страницу входа в браузере? (y/n): ").lower() == 'y':
            import webbrowser
            webbrowser.open(f"{self.ngrok_url}/login")
            self.print_success("Открыто в браузере")

        return True

    def test_google_api_connectivity(self):
        """Тест подключения к Google API"""
        self.print_header("ПРОВЕРКА ПОДКЛЮЧЕНИЯ К GOOGLE API")

        # Проверяем доступность Google OAuth2 endpoints
        google_endpoints = [
            ('https://accounts.google.com/.well-known/openid-configuration', 'OpenID Configuration'),
            ('https://www.googleapis.com/oauth2/v1/certs', 'Google Certificates'),
        ]

        for url, description in google_endpoints:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.print_success(f"{description}: доступен")
                else:
                    self.print_warning(f"{description}: код {response.status_code}")
            except requests.exceptions.RequestException:
                self.print_error(f"{description}: недоступен")

        return True

    def check_database(self):
        """Проверка базы данных пользователей"""
        self.print_header("ПРОВЕРКА БАЗЫ ДАННЫХ")

        db_path = 'users_history.db'

        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            self.print_success(f"База данных существует: {size} байт")

            # Проверяем структуру
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Проверяем таблицы
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                for table in tables:
                    self.print_info(f"Таблица: {table[0]}")

                    # Считаем записи
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    self.print_info(f"  Записей: {count}")

                conn.close()

            except sqlite3.Error as e:
                self.print_error(f"Ошибка чтения базы данных: {e}")
        else:
            self.print_warning("База данных не существует (будет создана при первом запуске)")

        return True

    def generate_report(self):
        """Генерация итогового отчета"""
        self.print_header("ИТОГОВЫЙ ОТЧЕТ")

        total_errors = len(self.errors)
        total_warnings = len(self.warnings)

        if total_errors == 0 and total_warnings == 0:
            print(f"\n{Fore.GREEN}{'=' * 60}")
            print(f"{Fore.GREEN}🎉 ОТЛИЧНО! Все проверки пройдены успешно!")
            print(f"{Fore.GREEN}{'=' * 60}")

            if self.ngrok_url:
                print(f"\n{Fore.CYAN}Ваше приложение доступно по адресу:")
                print(f"{Fore.GREEN}{self.ngrok_url}")
                print(f"\n{Fore.CYAN}Тестовый вход:")
                print(f"{Fore.GREEN}{self.ngrok_url}/login")

        elif total_errors == 0:
            print(f"\n{Fore.YELLOW}{'=' * 60}")
            print(f"{Fore.YELLOW}⚠️  Есть предупреждения: {total_warnings}")
            print(f"{Fore.YELLOW}{'=' * 60}")

            for warning in self.warnings[:5]:  # Показываем первые 5
                print(f"{Fore.YELLOW}• {warning}")

        else:
            print(f"\n{Fore.RED}{'=' * 60}")
            print(f"{Fore.RED}❌ Обнаружены ошибки: {total_errors}")
            print(f"{Fore.RED}{'=' * 60}")

            for error in self.errors[:5]:  # Показываем первые 5
                print(f"{Fore.RED}• {error}")

            print(f"\n{Fore.YELLOW}Рекомендации по исправлению:")

            if 'ngrok не установлен' in str(self.errors):
                print(f"{Fore.WHITE}1. Установите ngrok: https://ngrok.com/download")
                print(f"{Fore.WHITE}2. Настройте authtoken: ngrok config add-authtoken YOUR_TOKEN")

            if 'Flask приложение не запущено' in str(self.errors):
                print(f"{Fore.WHITE}1. Запустите Flask: python main.py")
                print(f"{Fore.WHITE}2. Проверьте порт 5001")

            if 'GOOGLE_CLIENT_ID' in str(self.errors) or 'GOOGLE_CLIENT_SECRET' in str(self.errors):
                print(f"{Fore.WHITE}1. Создайте OAuth2 credentials в Google Console")
                print(f"{Fore.WHITE}2. Добавьте в .env файл")

    def run_all_tests(self):
        """Запуск всех тестов"""
        print(f"\n{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.CYAN}🔧 ТЕСТИРОВАНИЕ OAUTH2 КОНФИГУРАЦИИ")
        print(f"{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.WHITE}Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Выполняем все проверки
        tests = [
            ("Переменные окружения", self.check_environment),
            ("ngrok", self.check_ngrok),
            ("Flask приложение", self.check_flask_app),
            ("OAuth2 endpoints", self.check_oauth_endpoints),
            ("Google API", self.test_google_api_connectivity),
            ("База данных", self.check_database),
        ]

        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.print_error(f"Ошибка при выполнении теста '{test_name}': {str(e)}")

        # Дополнительные проверки
        self.check_google_console_config()
        self.simulate_oauth_flow()

        # Итоговый отчет
        self.generate_report()


def quick_start():
    """Быстрый запуск с автоматической настройкой"""
    print(f"{Fore.CYAN}🚀 Быстрая настройка OAuth2 с ngrok")
    print(f"{Fore.CYAN}{'=' * 60}")

    # Проверяем наличие .env
    if not os.path.exists('.env'):
        print(f"{Fore.YELLOW}Создаем .env файл...")
        with open('.env', 'w') as f:
            f.write("""# OAuth2 Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Flask Configuration  
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development
FLASK_DEBUG=1

# Ngrok URL (обновляется автоматически)
NGROK_URL=
""")
        print(f"{Fore.GREEN}✅ Создан .env файл")
        print(f"{Fore.YELLOW}⚠️  Добавьте GOOGLE_CLIENT_ID и GOOGLE_CLIENT_SECRET!")
        return

    # Проверяем ngrok
    try:
        subprocess.run(['ngrok', 'version'], capture_output=True, timeout=2)
    except:
        print(f"{Fore.RED}❌ ngrok не установлен")
        print(f"{Fore.YELLOW}Установите с https://ngrok.com/download")
        return

    # Запускаем ngrok если не запущен
    try:
        requests.get('http://localhost:4040/api/tunnels', timeout=1)
        print(f"{Fore.GREEN}✅ ngrok уже запущен")
    except:
        print(f"{Fore.YELLOW}Запускаем ngrok...")
        subprocess.Popen(['ngrok', 'http', '5001'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        time.sleep(3)

    # Запускаем тестирование
    tester = OAuth2Tester()
    tester.run_all_tests()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_start()
    else:
        tester = OAuth2Tester()
        tester.run_all_tests()