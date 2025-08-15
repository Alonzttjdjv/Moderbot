import asyncio
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from database.models import Bot, BotConfig, User
from bot.telegram_bot import TelegramBot
from bot.discord_bot import DiscordBot
from bot.vk_bot import VKBot

logger = logging.getLogger(__name__)

class BotPlatform:
    """Основная платформа для управления ботами"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.active_bots: Dict[int, object] = {}
        self.platforms = {
            'telegram': TelegramBot,
            'discord': DiscordBot,
            'vk': VKBot
        }
    
    async def start_bot(self, bot_id: int) -> bool:
        """Запуск бота"""
        try:
            bot = self.db_session.query(Bot).filter(Bot.id == bot_id).first()
            if not bot or not bot.is_active:
                return False
            
            # Создаем экземпляр бота нужной платформы
            bot_class = self.platforms.get(bot.platform)
            if not bot_class:
                logger.error(f"Неподдерживаемая платформа: {bot.platform}")
                return False
            
            bot_instance = bot_class(bot, self.db_session)
            await bot_instance.start()
            
            self.active_bots[bot_id] = bot_instance
            logger.info(f"Бот {bot.name} успешно запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота {bot_id}: {e}")
            return False
    
    async def stop_bot(self, bot_id: int) -> bool:
        """Остановка бота"""
        try:
            if bot_id in self.active_bots:
                bot_instance = self.active_bots[bot_id]
                await bot_instance.stop()
                del self.active_bots[bot_id]
                logger.info(f"Бот {bot_id} остановлен")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка остановки бота {bot_id}: {e}")
            return False
    
    async def restart_bot(self, bot_id: int) -> bool:
        """Перезапуск бота"""
        await self.stop_bot(bot_id)
        return await self.start_bot(bot_id)
    
    async def start_all_bots(self) -> None:
        """Запуск всех активных ботов"""
        bots = self.db_session.query(Bot).filter(Bot.is_active == True).all()
        for bot in bots:
            await self.start_bot(bot.id)
    
    async def stop_all_bots(self) -> None:
        """Остановка всех ботов"""
        for bot_id in list(self.active_bots.keys()):
            await self.stop_bot(bot_id)
    
    def get_bot_config(self, bot_id: int, chat_id: str) -> Optional[BotConfig]:
        """Получение конфигурации бота для конкретного чата"""
        return self.db_session.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
    
    def update_bot_config(self, bot_id: int, chat_id: str, config_data: dict) -> bool:
        """Обновление конфигурации бота"""
        try:
            config = self.get_bot_config(bot_id, chat_id)
            if not config:
                return False
            
            # Обновляем настройки
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            self.db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
            self.db_session.rollback()
            return False
    
    def get_user_bots(self, user_id: int) -> List[Bot]:
        """Получение всех ботов пользователя"""
        return self.db_session.query(Bot).filter(Bot.user_id == user_id).all()
    
    def create_bot(self, user_id: int, name: str, platform: str, token: str) -> Optional[Bot]:
        """Создание нового бота"""
        try:
            bot = Bot(
                user_id=user_id,
                name=name,
                platform=platform,
                token=token
            )
            self.db_session.add(bot)
            self.db_session.commit()
            return bot
        except Exception as e:
            logger.error(f"Ошибка создания бота: {e}")
            self.db_session.rollback()
            return None
    
    def delete_bot(self, bot_id: int, user_id: int) -> bool:
        """Удаление бота"""
        try:
            bot = self.db_session.query(Bot).filter(
                Bot.id == bot_id,
                Bot.user_id == user_id
            ).first()
            
            if not bot:
                return False
            
            # Останавливаем бота если он запущен
            if bot_id in self.active_bots:
                asyncio.create_task(self.stop_bot(bot_id))
            
            self.db_session.delete(bot)
            self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления бота: {e}")
            self.db_session.rollback()
            return False