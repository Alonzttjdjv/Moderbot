#!/usr/bin/env python3
"""
Bot Platform - Основной файл запуска
Платформа для создания и настройки ботов с возможностью кастомизации
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from bot.platform import BotPlatform
from database.database import get_db, init_db
from web.main import app
import uvicorn

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot_platform.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BotPlatformRunner:
    """Основной класс для запуска платформы"""
    
    def __init__(self):
        self.platform = None
        self.web_app = app
    
    async def start_platform(self):
        """Запуск платформы"""
        try:
            logger.info("Запуск Bot Platform...")
            
            # Инициализируем базу данных
            await self._init_database()
            
            # Создаем экземпляр платформы
            db_session = next(get_db())
            self.platform = BotPlatform(db_session)
            
            # Запускаем все активные боты
            await self.platform.start_all_bots()
            
            logger.info("Bot Platform успешно запущен!")
            
        except Exception as e:
            logger.error(f"Ошибка запуска платформы: {e}")
            raise
    
    async def stop_platform(self):
        """Остановка платформы"""
        try:
            if self.platform:
                await self.platform.stop_all_bots()
                logger.info("Bot Platform остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки платформы: {e}")
    
    async def _init_database(self):
        """Инициализация базы данных"""
        try:
            await init_db()
            logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    def run_web_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Запуск веб-сервера"""
        try:
            logger.info(f"Запуск веб-сервера на {host}:{port}")
            uvicorn.run(
                self.web_app,
                host=host,
                port=port,
                log_level="info"
            )
        except Exception as e:
            logger.error(f"Ошибка запуска веб-сервера: {e}")
            raise

async def main():
    """Главная функция"""
    runner = BotPlatformRunner()
    
    try:
        # Запускаем платформу
        await runner.start_platform()
        
        # Запускаем веб-сервер
        runner.run_web_server()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        # Останавливаем платформу
        await runner.stop_platform()

if __name__ == "__main__":
    # Создаем директорию для логов
    os.makedirs("logs", exist_ok=True)
    
    # Запускаем платформу
    asyncio.run(main())