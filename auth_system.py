#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAuth2 Google авторизация и система истории конвертаций
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import session, redirect, url_for, request, jsonify, render_template
from authlib.integrations.flask_client import OAuth
import logging

logger = logging.getLogger('ifc-exporter')


class AuthManager:
    """Менеджер авторизации и истории пользователей"""

    def __init__(self, app):
        self.app = app
        self.oauth = OAuth(app)
        self.setup_database()
        self.setup_google_oauth()

    def setup_database(self):
        """Создание базы данных для хранения истории"""
        db_path = 'users_history.db'

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица истории конвертаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                original_filename TEXT,
                csv_filename TEXT,
                sheet_url TEXT,
                file_size INTEGER,
                processed_flats INTEGER,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processing_time_seconds REAL,
                status TEXT DEFAULT 'success',
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def setup_google_oauth(self):
        """Настройка Google OAuth2"""
        # Регистрация Google OAuth провайдера
        self.google = self.oauth.register(
            name='google',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )

    def login_required(self, f):
        """Декоратор для проверки авторизации"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                # Для API запросов возвращаем JSON
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                # Для веб-интерфейса перенаправляем на логин
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    def save_user(self, user_info):
        """Сохранение информации о пользователе"""
        conn = sqlite3.connect('users_history.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO users (id, email, name, picture, last_login)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_info['sub'],
            user_info['email'],
            user_info.get('name', ''),
            user_info.get('picture', ''),
            datetime.now()
        ))

        conn.commit()
        conn.close()

    def save_conversion(self, user_id, conversion_data):
        """Сохранение записи о конвертации"""
        conn = sqlite3.connect('users_history.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO conversions 
            (user_id, original_filename, csv_filename, sheet_url, file_size, 
             processed_flats, processing_time_seconds, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            conversion_data.get('original_filename'),
            conversion_data.get('csv_filename'),
            conversion_data.get('sheet_url'),
            conversion_data.get('file_size', 0),
            conversion_data.get('processed_flats', 0),
            conversion_data.get('processing_time', 0.0),
            conversion_data.get('status', 'success'),
            conversion_data.get('error_message')
        ))

        conn.commit()
        conn.close()

    def get_user_history(self, user_id, limit=50):
        """Получение истории конвертаций пользователя"""
        conn = sqlite3.connect('users_history.db')
        conn.row_factory = sqlite3.Row  # Для доступа по именам колонок
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM conversions 
            WHERE user_id = ? 
            ORDER BY upload_time DESC 
            LIMIT ?
        ''', (user_id, limit))

        history = cursor.fetchall()
        conn.close()

        # Конвертируем в список словарей
        return [dict(row) for row in history]

    def get_user_stats(self, user_id):
        """Получение статистики пользователя"""
        conn = sqlite3.connect('users_history.db')
        cursor = conn.cursor()

        # Общее количество конвертаций
        cursor.execute('SELECT COUNT(*) FROM conversions WHERE user_id = ?', (user_id,))
        total_conversions = cursor.fetchone()[0]

        # Успешные конвертации
        cursor.execute(
            'SELECT COUNT(*) FROM conversions WHERE user_id = ? AND status = "success"',
            (user_id,)
        )
        successful_conversions = cursor.fetchone()[0]

        # Общее количество обработанных квартир
        cursor.execute(
            'SELECT SUM(processed_flats) FROM conversions WHERE user_id = ? AND status = "success"',
            (user_id,)
        )
        total_flats = cursor.fetchone()[0] or 0

        # Конвертации за последний месяц
        last_month = datetime.now() - timedelta(days=30)
        cursor.execute(
            'SELECT COUNT(*) FROM conversions WHERE user_id = ? AND upload_time > ?',
            (user_id, last_month)
        )
        recent_conversions = cursor.fetchone()[0]

        conn.close()

        return {
            'total_conversions': total_conversions,
            'successful_conversions': successful_conversions,
            'total_flats_processed': total_flats,
            'recent_conversions': recent_conversions,
            'success_rate': (successful_conversions / total_conversions * 100) if total_conversions > 0 else 0
        }


def setup_auth_routes(app, auth_manager):
    """Настройка маршрутов авторизации"""

    @app.route('/login')
    def login():
        """Страница входа"""
        if 'user' in session:
            return redirect(url_for('dashboard'))

        google_redirect_uri = url_for('auth_callback', _external=True)
        return auth_manager.google.authorize_redirect(google_redirect_uri)

    @app.route('/auth/callback')
    def auth_callback():
        """Обработка callback от Google OAuth"""
        try:
            token = auth_manager.google.authorize_access_token()
            user_info = token.get('userinfo')

            if user_info:
                # Сохраняем информацию о пользователе
                auth_manager.save_user(user_info)

                # Сохраняем в сессию
                session['user'] = {
                    'id': user_info['sub'],
                    'email': user_info['email'],
                    'name': user_info.get('name', ''),
                    'picture': user_info.get('picture', '')
                }

                logger.info(f"User logged in: {user_info['email']}")
                return redirect(url_for('dashboard'))
            else:
                logger.error("Failed to get user info from Google")
                return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            return redirect(url_for('index'))

    @app.route('/logout')
    def logout():
        """Выход из системы"""
        session.pop('user', None)
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @auth_manager.login_required
    def dashboard():
        """Личный кабинет пользователя"""
        user_id = session['user']['id']

        # Получаем статистику и историю
        stats = auth_manager.get_user_stats(user_id)
        history = auth_manager.get_user_history(user_id, limit=20)

        return render_template('dashboard.html',
                               user=session['user'],
                               stats=stats,
                               history=history)

    @app.route('/api/history')
    @auth_manager.login_required
    def api_history():
        """API для получения истории конвертаций"""
        user_id = session['user']['id']
        limit = request.args.get('limit', 50, type=int)

        history = auth_manager.get_user_history(user_id, limit)
        return jsonify({
            'status': 'success',
            'history': history
        })

    @app.route('/api/stats')
    @auth_manager.login_required
    def api_stats():
        """API для получения статистики пользователя"""
        user_id = session['user']['id']
        stats = auth_manager.get_user_stats(user_id)

        return jsonify({
            'status': 'success',
            'stats': stats
        })


def create_dashboard_template():
    """HTML шаблон для панели управления пользователя"""
    return '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IFC Converter - Панель управления</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }

        .header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .user-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .user-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid white;
        }

        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }

        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 10px;
        }

        .stat-label {
            color: #666;
            font-size: 1.1em;
        }

        .history-section {
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .section-header {
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            padding: 20px;
            font-size: 1.3em;
            font-weight: 600;
        }

        .upload-section {
            padding: 30px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }

        .history-table {
            width: 100%;
            border-collapse: collapse;
        }

        .history-table th,
        .history-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        .history-table th {
            background: #f8f9fa;
            font-weight: 600;
        }

        .status-success {
            color: #28a745;
            font-weight: 600;
        }

        .status-error {
            color: #dc3545;
            font-weight: 600;
        }

        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            border: none;
            cursor: pointer;
            transition: transform 0.2s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .btn-danger {
            background: linear-gradient(45deg, #dc3545, #c82333);
        }

        .file-input {
            margin: 20px 0;
        }

        .upload-form {
            display: flex;
            flex-direction: column;
            gap: 20px;
            align-items: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏗️ IFC Converter</h1>
        <div class="user-info">
            <img src="{{ user.picture }}" alt="{{ user.name }}" class="user-avatar">
            <div>
                <div>{{ user.name }}</div>
                <div style="font-size: 0.9em; opacity: 0.8;">{{ user.email }}</div>
            </div>
            <a href="{{ url_for('logout') }}" class="btn btn-danger">Выйти</a>
        </div>
    </div>

    <div class="container">
        <!-- Статистика -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_conversions }}</div>
                <div class="stat-label">Всего конвертаций</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_flats_processed }}</div>
                <div class="stat-label">Обработано квартир</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ "%.1f"|format(stats.success_rate) }}%</div>
                <div class="stat-label">Успешность</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.recent_conversions }}</div>
                <div class="stat-label">За последний месяц</div>
            </div>
        </div>

        <!-- Загрузка файла -->
        <div class="history-section">
            <div class="section-header">📤 Загрузить новый IFC файл</div>
            <div class="upload-section">
                <form class="upload-form" id="uploadForm" enctype="multipart/form-data">
                    <div class="file-input">
                        <input type="file" id="fileInput" name="file" accept=".ifc,.ifczip" required>
                    </div>
                    <button type="submit" class="btn">Загрузить и конвертировать</button>
                </form>
                <div id="uploadStatus" style="margin-top: 20px;"></div>
            </div>
        </div>

        <!-- История конвертаций -->
        <div class="history-section" style="margin-top: 20px;">
            <div class="section-header">📋 История конвертаций</div>
            {% if history %}
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>Файл</th>
                        <th>Квартир</th>
                        <th>Статус</th>
                        <th>Google Sheets</th>
                        <th>Скачать</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in history %}
                    <tr>
                        <td>{{ item.upload_time[:16] }}</td>
                        <td>{{ item.original_filename }}</td>
                        <td>{{ item.processed_flats or 0 }}</td>
                        <td>
                            <span class="status-{{ item.status }}">
                                {{ 'Успешно' if item.status == 'success' else 'Ошибка' }}
                            </span>
                        </td>
                        <td>
                            {% if item.sheet_url %}
                                <a href="{{ item.sheet_url }}" target="_blank" class="btn" style="padding: 6px 12px; font-size: 0.9em;">Открыть</a>
                            {% else %}
                                -
                            {% endif %}
                        </td>
                        <td>
                            {% if item.csv_filename %}
                                <a href="{{ url_for('download_file', filename=item.csv_filename) }}" class="btn" style="padding: 6px 12px; font-size: 0.9em;">CSV</a>
                            {% else %}
                                -
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div style="padding: 40px; text-align: center; color: #666;">
                <p>История пуста. Загрузите свой первый IFC файл!</p>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const fileInput = document.getElementById('fileInput');
            const statusDiv = document.getElementById('uploadStatus');
            const submitBtn = this.querySelector('button[type="submit"]');

            if (!fileInput.files.length) {
                statusDiv.innerHTML = '<div style="color: red;">Выберите файл</div>';
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            submitBtn.disabled = true;
            submitBtn.textContent = 'Обработка...';
            statusDiv.innerHTML = '<div style="color: blue;">⏳ Загружаем и обрабатываем файл...</div>';

            try {
                const response = await fetch('/uploads', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.status === 'success') {
                    statusDiv.innerHTML = `
                        <div style="color: green;">
                            ✅ Файл успешно обработан!<br>
                            ${result.sheet_url ? '<a href="' + result.sheet_url + '" target="_blank">Открыть в Google Sheets</a>' : ''}
                        </div>
                    `;
                    // Перезагружаем страницу через 2 секунды для обновления истории
                    setTimeout(() => location.reload(), 2000);
                } else {
                    statusDiv.innerHTML = '<div style="color: red;">❌ ' + (result.error || 'Ошибка обработки') + '</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = '<div style="color: red;">❌ Ошибка сети: ' + error.message + '</div>';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Загрузить и конвертировать';
            }
        });
    </script>
</body>
</html>'''