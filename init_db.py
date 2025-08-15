#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных Bot Platform
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from database.database import create_tables, create_user
from database.models import User, Bot, BotConfig, BotTemplate
from sqlalchemy.orm import Session
from database.database import SessionLocal
import hashlib

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_sample_data():
    """Создание тестовых данных"""
    db = SessionLocal()
    try:
        # Создаем тестового пользователя
        test_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            is_active=True
        )
        db.add(test_user)
        db.commit()
        
        print("Тестовый пользователь создан:")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        print(f"  Email: admin@example.com")
        
        # Создаем тестового бота
        test_bot = Bot(
            user_id=test_user.id,
            name="Test Bot",
            platform="telegram",
            token="your_telegram_token_here",
            is_active=True
        )
        db.add(test_bot)
        db.commit()
        
        print(f"\nТестовый бот создан:")
        print(f"  Name: {test_bot.name}")
        print(f"  Platform: {test_bot.platform}")
        print(f"  ID: {test_bot.id}")
        
        # Создаем шаблоны ботов
        templates = [
            {
                "name": "Customer Support Bot",
                "description": "Бот для поддержки клиентов с автоответами",
                "platform": "telegram",
                "config_schema": {
                    "welcome_message": "string",
                    "auto_responses": "object",
                    "working_hours": "string"
                },
                "default_config": {
                    "welcome_message": "Добро пожаловать! Чем могу помочь?",
                    "auto_responses": {
                        "привет": "Здравствуйте! Опишите вашу проблему.",
                        "спасибо": "Пожалуйста! Обращайтесь еще."
                    },
                    "working_hours": "Пн-Пт 9:00-18:00"
                }
            },
            {
                "name": "Moderation Bot",
                "description": "Бот для модерации чатов с фильтрами",
                "platform": "discord",
                "config_schema": {
                    "blocked_words": "array",
                    "warn_threshold": "number",
                    "auto_delete": "boolean"
                },
                "default_config": {
                    "blocked_words": ["спам", "реклама", "оскорбления"],
                    "warn_threshold": 3,
                    "auto_delete": True
                }
            }
        ]
        
        for template_data in templates:
            template = BotTemplate(**template_data)
            db.add(template)
        
        db.commit()
        print(f"\nСоздано {len(templates)} шаблонов ботов")
        
    except Exception as e:
        print(f"Ошибка создания тестовых данных: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Главная функция"""
    print("Bot Platform - Инициализация базы данных")
    print("=" * 50)
    
    try:
        # Создаем таблицы
        print("Создание таблиц...")
        create_tables()
        print("✓ Таблицы созданы успешно")
        
        # Создаем тестовые данные
        print("\nСоздание тестовых данных...")
        create_sample_data()
        print("✓ Тестовые данные созданы успешно")
        
        print("\n" + "=" * 50)
        print("База данных инициализирована успешно!")
        print("\nДля запуска платформы выполните:")
        print("  python main.py")
        print("\nДля входа используйте:")
        print("  Username: admin")
        print("  Password: admin123")
        
    except Exception as e:
        print(f"\n❌ Ошибка инициализации: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()