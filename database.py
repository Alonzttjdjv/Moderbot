import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица чатов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER PRIMARY KEY,
                        chat_title TEXT,
                        chat_type TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        settings TEXT DEFAULT '{}',
                        admin_ids TEXT DEFAULT '[]'
                    )
                ''')
                
                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_banned BOOLEAN DEFAULT 0,
                        ban_reason TEXT,
                        ban_until TIMESTAMP,
                        warnings INTEGER DEFAULT 0,
                        total_messages INTEGER DEFAULT 0,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица действий модерации
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS moderation_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        user_id INTEGER,
                        action_type TEXT,
                        reason TEXT,
                        moderator_id INTEGER,
                        duration INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица сообщений
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        user_id INTEGER,
                        message_id INTEGER,
                        message_type TEXT,
                        content TEXT,
                        is_deleted BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица статистики
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        date DATE,
                        total_messages INTEGER DEFAULT 0,
                        new_users INTEGER DEFAULT 0,
                        deleted_messages INTEGER DEFAULT 0,
                        moderation_actions INTEGER DEFAULT 0,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                    )
                ''')
                
                # Таблица фильтров
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS filters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        filter_type TEXT,
                        pattern TEXT,
                        action TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                    )
                ''')
                
                # Таблица временных банов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS temp_bans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER,
                        user_id INTEGER,
                        ban_type TEXT,
                        reason TEXT,
                        moderator_id INTEGER,
                        ban_until TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Создаем индексы для оптимизации
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON messages (chat_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON messages (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_type ON moderation_actions (action_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ban_until ON temp_bans (ban_until)')
                
                conn.commit()
                logger.info("База данных успешно инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
    
    def add_chat(self, chat_id: int, chat_title: str, chat_type: str, admin_ids: List[int] = None) -> bool:
        """Добавление нового чата"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                admin_ids_json = json.dumps(admin_ids or [])
                cursor.execute('''
                    INSERT OR REPLACE INTO chats (chat_id, chat_title, chat_type, admin_ids)
                    VALUES (?, ?, ?, ?)
                ''', (chat_id, chat_title, chat_type, admin_ids_json))
                conn.commit()
                logger.info(f"Чат {chat_id} добавлен в базу данных")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления чата: {e}")
            return False
    
    def get_chat(self, chat_id: int) -> Optional[Dict]:
        """Получение информации о чате"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM chats WHERE chat_id = ?', (chat_id,))
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    chat_data = dict(zip(columns, row))
                    chat_data['admin_ids'] = json.loads(chat_data['admin_ids'])
                    chat_data['settings'] = json.loads(chat_data['settings'])
                    return chat_data
                return None
        except Exception as e:
            logger.error(f"Ошибка получения чата: {e}")
            return None
    
    def update_chat_settings(self, chat_id: int, settings: Dict) -> bool:
        """Обновление настроек чата"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                settings_json = json.dumps(settings)
                cursor.execute('''
                    UPDATE chats SET settings = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                ''', (settings_json, chat_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка обновления настроек чата: {e}")
            return False
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Добавление нового пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def add_moderation_action(self, chat_id: int, user_id: int, action_type: str, 
                            reason: str, moderator_id: int, duration: int = 0) -> bool:
        """Добавление действия модерации"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO moderation_actions (chat_id, user_id, action_type, reason, moderator_id, duration)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (chat_id, user_id, action_type, reason, moderator_id, duration))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления действия модерации: {e}")
            return False
    
    def add_message(self, chat_id: int, user_id: int, message_id: int, 
                   message_type: str, content: str = None) -> bool:
        """Добавление сообщения"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages (chat_id, user_id, message_id, message_type, content)
                    VALUES (?, ?, ?, ?, ?)
                ''', (chat_id, user_id, message_id, message_type, content))
                
                # Обновляем статистику пользователя
                cursor.execute('''
                    UPDATE users SET total_messages = total_messages + 1, 
                    last_activity = CURRENT_TIMESTAMP WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления сообщения: {e}")
            return False
    
    def mark_message_deleted(self, chat_id: int, message_id: int) -> bool:
        """Отметка сообщения как удаленного"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE messages SET is_deleted = 1 WHERE chat_id = ? AND message_id = ?
                ''', (chat_id, message_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка отметки сообщения как удаленного: {e}")
            return False
    
    def add_temp_ban(self, chat_id: int, user_id: int, ban_type: str, reason: str, 
                     moderator_id: int, duration: int) -> bool:
        """Добавление временного бана"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                ban_until = datetime.now() + timedelta(seconds=duration)
                cursor.execute('''
                    INSERT INTO temp_bans (chat_id, user_id, ban_type, reason, moderator_id, ban_until)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (chat_id, user_id, ban_type, reason, moderator_id, ban_until))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления временного бана: {e}")
            return False
    
    def get_active_temp_bans(self, chat_id: int = None) -> List[Dict]:
        """Получение активных временных банов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if chat_id:
                    cursor.execute('''
                        SELECT * FROM temp_bans WHERE chat_id = ? AND is_active = 1 AND ban_until > CURRENT_TIMESTAMP
                    ''', (chat_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM temp_bans WHERE is_active = 1 AND ban_until > CURRENT_TIMESTAMP
                    ''')
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения временных банов: {e}")
            return []
    
    def expire_temp_bans(self) -> int:
        """Истечение временных банов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE temp_bans SET is_active = 0 
                    WHERE ban_until <= CURRENT_TIMESTAMP AND is_active = 1
                ''')
                expired_count = cursor.rowcount
                conn.commit()
                return expired_count
        except Exception as e:
            logger.error(f"Ошибка истечения временных банов: {e}")
            return 0
    
    def get_chat_statistics(self, chat_id: int, days: int = 7) -> Dict:
        """Получение статистики чата"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Общее количество сообщений
                cursor.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ?', (chat_id,))
                total_messages = cursor.fetchone()[0]
                
                # Сообщения за последние N дней
                cursor.execute('''
                    SELECT COUNT(*) FROM messages 
                    WHERE chat_id = ? AND created_at >= datetime('now', '-{} days')
                '''.format(days), (chat_id,))
                recent_messages = cursor.fetchone()[0]
                
                # Количество пользователей
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) FROM messages WHERE chat_id = ?
                ''', (chat_id,))
                unique_users = cursor.fetchone()[0]
                
                # Действия модерации
                cursor.execute('''
                    SELECT COUNT(*) FROM moderation_actions 
                    WHERE chat_id = ? AND created_at >= datetime('now', '-{} days')
                '''.format(days), (chat_id,))
                moderation_actions = cursor.fetchone()[0]
                
                return {
                    'total_messages': total_messages,
                    'recent_messages': recent_messages,
                    'unique_users': unique_users,
                    'moderation_actions': moderation_actions,
                    'period_days': days
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Очистка старых данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Удаляем старые сообщения
                cursor.execute('''
                    DELETE FROM messages 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                deleted_messages = cursor.rowcount
                
                # Удаляем старые действия модерации
                cursor.execute('''
                    DELETE FROM moderation_actions 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                deleted_actions = cursor.rowcount
                
                conn.commit()
                return deleted_messages + deleted_actions
        except Exception as e:
            logger.error(f"Ошибка очистки старых данных: {e}")
            return 0

# Создаем глобальный экземпляр менеджера базы данных
db = DatabaseManager()