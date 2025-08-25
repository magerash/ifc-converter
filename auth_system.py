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
        # db_path = 'users_history.db'
        db_path = db_path = os.getenv('DB_PATH', 'users_history.db') # ======================= ВТОРОЙ СЕРВЕР ======================= #

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

