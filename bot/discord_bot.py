import asyncio
import logging
from typing import Optional, Dict, Any
import discord
from discord.ext import commands
from sqlalchemy.orm import Session
from database.models import Bot as BotModel, BotConfig

logger = logging.getLogger(__name__)

class DiscordBot:
    """Discord бот с возможностью кастомизации"""
    
    def __init__(self, bot_model: BotModel, db_session: Session):
        self.bot_model = bot_model
        self.db_session = db_session
        self.bot = commands.Bot(
            command_prefix='!',
            intents=discord.Intents.default(),
            help_command=None
        )
        self.is_running = False
        
        # Регистрируем обработчики событий
        self._register_events()
        self._register_commands()
    
    def _register_events(self):
        """Регистрация обработчиков событий"""
        
        @self.bot.event
        async def on_ready():
            """Событие готовности бота"""
            logger.info(f"Discord бот {self.bot_model.name} готов к работе")
            logger.info(f"Подключен к {len(self.bot.guilds)} серверам")
            self.is_running = True
        
        @self.bot.event
        async def on_message(message):
            """Обработка всех сообщений"""
            # Игнорируем сообщения от ботов
            if message.author.bot:
                return
            
            # Получаем конфигурацию для этого сервера/канала
            guild_id = str(message.guild.id) if message.guild else "DM"
            channel_id = str(message.channel.id)
            
            config = self._get_chat_config(guild_id, channel_id)
            if not config:
                # Создаем конфигурацию если её нет
                self._ensure_chat_config(guild_id, channel_id, message.guild.name if message.guild else "DM")
                config = self._get_chat_config(guild_id, channel_id)
            
            # Проверяем автоответы
            if config and config.responses:
                response = self._check_auto_response(message.content, config.responses)
                if response:
                    await message.channel.send(response)
                    return
            
            # Проверяем фильтры
            if config and config.filters and self._should_filter_message(message.content, config.filters):
                await message.delete()
                await message.channel.send("Сообщение заблокировано фильтром.")
                return
            
            # Обновляем статистику
            self._update_message_count(guild_id, channel_id)
            
            # Обрабатываем команды
            await self.bot.process_commands(message)
    
    def _register_commands(self):
        """Регистрация команд"""
        
        @self.bot.command(name='start')
        async def start_command(ctx):
            """Команда /start"""
            guild_id = str(ctx.guild.id) if ctx.guild else "DM"
            channel_id = str(ctx.channel.id)
            
            config = self._get_chat_config(guild_id, channel_id)
            
            if config and config.welcome_message:
                welcome_msg = config.welcome_message
            else:
                welcome_msg = f"Привет! Я бот {self.bot_model.name}. Используйте !help для получения справки."
            
            await ctx.send(welcome_msg)
        
        @self.bot.command(name='help')
        async def help_command(ctx):
            """Команда /help"""
            guild_id = str(ctx.guild.id) if ctx.guild else "DM"
            channel_id = str(ctx.channel.id)
            
            config = self._get_chat_config(guild_id, channel_id)
            
            help_text = "**Доступные команды:**\n"
            help_text += "• `!start` - Начать работу с ботом\n"
            help_text += "• `!help` - Показать эту справку\n"
            help_text += "• `!settings` - Настройки бота\n"
            
            # Добавляем кастомные команды
            if config and config.commands:
                for cmd, desc in config.commands.items():
                    help_text += f"• `!{cmd}` - {desc}\n"
            
            await ctx.send(help_text)
        
        @self.bot.command(name='settings')
        async def settings_command(ctx):
            """Команда /settings"""
            guild_id = str(ctx.guild.id) if ctx.guild else "DM"
            channel_id = str(ctx.channel.id)
            
            config = self._get_chat_config(guild_id, channel_id)
            
            if not config:
                await ctx.send("Настройки не найдены для этого канала.")
                return
            
            settings_text = f"**Настройки бота для канала:**\n\n"
            settings_text += f"**Приветственное сообщение:** {config.welcome_message or 'Не задано'}\n"
            settings_text += f"**Тип чата:** {config.chat_type or 'Не определен'}\n"
            settings_text += f"**Сообщений обработано:** {config.message_count}\n"
            
            await ctx.send(settings_text)
        
        @self.bot.command(name='ping')
        async def ping_command(ctx):
            """Команда /ping для проверки задержки"""
            latency = round(self.bot.latency * 1000)
            await ctx.send(f"🏓 Pong! Задержка: {latency}ms")
    
    async def start(self):
        """Запуск бота"""
        try:
            logger.info(f"Запуск Discord бота {self.bot_model.name}")
            await self.bot.start(self.bot_model.token)
        except Exception as e:
            logger.error(f"Ошибка запуска Discord бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        try:
            if self.bot.is_ready():
                await self.bot.close()
            self.is_running = False
            logger.info(f"Discord бот {self.bot_model.name} остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки Discord бота: {e}")
    
    def _get_chat_config(self, guild_id: str, channel_id: str) -> Optional[BotConfig]:
        """Получение конфигурации для сервера/канала"""
        return self.db_session.query(BotConfig).filter(
            BotConfig.bot_id == self.bot_model.id,
            BotConfig.chat_id == f"{guild_id}:{channel_id}"
        ).first()
    
    def _ensure_chat_config(self, guild_id: str, channel_id: str, chat_name: str):
        """Создание конфигурации если её нет"""
        chat_id = f"{guild_id}:{channel_id}"
        config = self._get_chat_config(guild_id, channel_id)
        
        if not config:
            config = BotConfig(
                bot_id=self.bot_model.id,
                user_id=self.bot_model.user_id,
                chat_id=chat_id,
                chat_name=chat_name,
                chat_type="guild" if guild_id != "DM" else "private"
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
        if "blocked_words" in filters:
            blocked_words = filters["blocked_words"]
            message_lower = message.lower()
            for word in blocked_words:
                if word.lower() in message_lower:
                    return True
        return False
    
    def _update_message_count(self, guild_id: str, channel_id: str):
        """Обновление счетчика сообщений"""
        try:
            config = self._get_chat_config(guild_id, channel_id)
            if config:
                config.message_count += 1
                self.db_session.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления счетчика сообщений: {e}")
    
    def update_config(self, guild_id: str, channel_id: str, config_data: Dict[str, Any]) -> bool:
        """Обновление конфигурации бота"""
        try:
            config = self._get_chat_config(guild_id, channel_id)
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
    
    async def send_message(self, guild_id: str, channel_id: str, message: str):
        """Отправка сообщения в канал"""
        try:
            if not self.bot.is_ready():
                return False
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return False
            
            channel = guild.get_channel(int(channel_id))
            if not channel:
                return False
            
            await channel.send(message)
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False