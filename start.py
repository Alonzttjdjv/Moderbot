#!/usr/bin/env python3
"""
Скрипт запуска Telegram Chat Moderator Bot
Обрабатывает инициализацию, проверку зависимостей и запуск бота
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

def check_dependencies():
    """Проверка необходимых зависимостей"""
    try:
        import aiogram
        import dotenv
        import aiofiles
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости командой: pip install -r requirements.txt")
        return False

def check_config():
    """Проверка конфигурации"""
    try:
        # Проверяем наличие .env файла
        if not os.path.exists('.env'):
            if os.path.exists('.env.example'):
                print("⚠️  Файл .env не найден")
                print("Скопируйте .env.example в .env и настройте параметры")
                return False
            else:
                print("❌ Файл .env.example не найден")
                return False
        
        # Проверяем основные параметры
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token or bot_token == 'your_bot_token_here':
            print("❌ Не настроен BOT_TOKEN в .env файле")
            return False
        
        print("✅ Конфигурация проверена")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")
        return False

def create_directories():
    """Создание необходимых директорий"""
    try:
        directories = ['data', 'backups', 'logs']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        print("✅ Директории созданы")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания директорий: {e}")
        return False

def setup_logging():
    """Настройка логирования"""
    try:
        # Создаем директорию для логов
        Path('logs').mkdir(exist_ok=True)
        
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bot.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        print("✅ Логирование настроено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настройки логирования: {e}")
        return False

async def main():
    """Основная функция запуска"""
    print("🚀 Запуск Telegram Chat Moderator Bot...")
    print("=" * 50)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not check_config():
        sys.exit(1)
    
    # Создаем директории
    if not create_directories():
        sys.exit(1)
    
    # Настраиваем логирование
    if not setup_logging():
        sys.exit(1)
    
    print("=" * 50)
    print("✅ Все проверки пройдены успешно")
    print("🚀 Запуск бота...")
    print("=" * 50)
    
    try:
        # Импортируем и запускаем основной модуль
        from main import main as bot_main
        await bot_main()
        
    except KeyboardInterrupt:
        print("\n⏹️  Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)