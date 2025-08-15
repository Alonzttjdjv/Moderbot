import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from database.models import Bot as BotModel, BotConfig

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram бот с возможностью кастомизации"""
    
    def __init__(self, bot_model: BotModel, db_session: Session):
        self.bot_model = bot_model
        self.db_session = db_session
        self.bot = Bot(token=bot_model.token)
        self.application: Optional[Application] = None
        self.is_running = False
    
    async def start(self):
        """Запуск бота"""
        try:
            self.application = Application.builder().token(self.bot_model.token).build()
            
            # Регистрируем обработчики
            self._register_handlers()
            
            # Запускаем бота
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info(f"Telegram бот {self.bot_model.name} запущен")
            
        except Exception as e:
            logger.error(f"Ошибка запуска Telegram бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            self.is_running = False
            logger.info(f"Telegram бот {self.bot_model.name} остановлен")
            
        except Exception as e:
            logger.error(f"Ошибка остановки Telegram бота: {e}")
    
    def _register_handlers(self):
        """Регистрация обработчиков команд и сообщений"""
        if not self.application:
            return
        
        # Базовые команды
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("settings", self._settings_command))
        
        # Обработчик всех сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Обработчик callback запросов
        # self.application.add_handler(CallbackQueryHandler(self._handle_callback))
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        chat_id = str(update.effective_chat.id)
        user_id = update.effective_user.id
        
        # Получаем конфигурацию для этого чата
        config = self._get_chat_config(chat_id)
        
        if config and config.welcome_message:
            welcome_msg = config.welcome_message
        else:
            welcome_msg = f"Привет! Я бот {self.bot_model.name}. Используйте /help для получения справки."
        
        await update.message.reply_text(welcome_msg)
        
        # Создаем или обновляем конфигурацию чата
        self._ensure_chat_config(chat_id, update.effective_chat.title or "Private Chat")
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        chat_id = str(update.effective_chat.id)
        config = self._get_chat_config(chat_id)
        
        help_text = "Доступные команды:\n"
        help_text += "/start - Начать работу с ботом\n"
        help_text += "/help - Показать эту справку\n"
        help_text += "/settings - Настройки бота\n"
        
        # Добавляем кастомные команды
        if config and config.commands:
            for cmd, desc in config.commands.items():
                help_text += f"/{cmd} - {desc}\n"
        
        await update.message.reply_text(help_text)
    
    async def _settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /settings"""
        chat_id = str(update.effective_chat.id)
        config = self._get_chat_config(chat_id)
        
        if not config:
            await update.message.reply_text("Настройки не найдены для этого чата.")
            return
        
        settings_text = f"Настройки бота для чата:\n\n"
        settings_text += f"Приветственное сообщение: {config.welcome_message or 'Не задано'}\n"
        settings_text += f"Тип чата: {config.chat_type or 'Не определен'}\n"
        settings_text += f"Сообщений обработано: {config.message_count}\n"
        
        await update.message.reply_text(settings_text)
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка всех сообщений"""
        chat_id = str(update.effective_chat.id)
        message_text = update.message.text
        
        # Получаем конфигурацию чата
        config = self._get_chat_config(chat_id)
        if not config:
            return
        
        # Проверяем автоответы
        if config.responses:
            response = self._check_auto_response(message_text, config.responses)
            if response:
                await update.message.reply_text(response)
                return
        
        # Проверяем фильтры
        if config.filters and self._should_filter_message(message_text, config.filters):
            await update.message.delete()
            await update.message.reply_text("Сообщение заблокировано фильтром.")
            return
        
        # Обновляем статистику
        self._update_message_count(chat_id)
    
    def _get_chat_config(self, chat_id: str) -> Optional[BotConfig]:
        """Получение конфигурации чата"""
        return self.db_session.query(BotConfig).filter(
            BotConfig.bot_id == self.bot_model.id,
            BotConfig.chat_id == chat_id
        ).first()
    
    def _ensure_chat_config(self, chat_id: str, chat_name: str):
        """Создание конфигурации чата если её нет"""
        config = self._get_chat_config(chat_id)
        if not config:
            config = BotConfig(
                bot_id=self.bot_model.id,
                user_id=self.bot_model.user_id,
                chat_id=chat_id,
                chat_name=chat_name,
                chat_type="group" if chat_name else "private"
            )
            self.db_session.add(config)
            self.db_session.commit()
    
    def _check_auto_response(self, message: str, responses: Dict[str, str]) -> Optional[str]:
        """Проверка автоответов"""
        message_lower = message.lower()
        for trigger, response in responses.items():
            if trigger.lower() in message_lower:
                return response
        return None
    
    def _should_filter_message(self, message: str, filters: Dict[str, Any]) -> bool:
        """Проверка фильтров сообщений"""
        # Простая реализация фильтров
        if "blocked_words" in filters:
            blocked_words = filters["blocked_words"]
            message_lower = message.lower()
            for word in blocked_words:
                if word.lower() in message_lower:
                    return True
        return False
    
    def _update_message_count(self, chat_id: str):
        """Обновление счетчика сообщений"""
        try:
            config = self._get_chat_config(chat_id)
            if config:
                config.message_count += 1
                self.db_session.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления счетчика сообщений: {e}")
    
    def update_config(self, chat_id: str, config_data: Dict[str, Any]) -> bool:
        """Обновление конфигурации бота"""
        try:
            config = self._get_chat_config(chat_id)
            if not config:
                return False
            
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            self.db_session.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации: {e}")
            self.db_session.rollback()
            return False