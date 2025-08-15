import asyncio
import logging
from typing import Optional, Dict, Any
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from sqlalchemy.orm import Session
from database.models import Bot as BotModel, BotConfig

logger = logging.getLogger(__name__)

class VKBot:
    """VK бот с возможностью кастомизации"""
    
    def __init__(self, bot_model: BotModel, db_session: Session):
        self.bot_model = bot_model
        self.db_session = db_session
        self.vk_session = vk_api.VkApi(token=bot_model.token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, bot_model.group_id)
        self.is_running = False
        
        # Регистрируем обработчики команд
        self._register_commands()
    
    def _register_commands(self):
        """Регистрация команд"""
        self.commands = {
            'start': self._start_command,
            'help': self._help_command,
            'settings': self._settings_command,
            'ping': self._ping_command
        }
    
    async def start(self):
        """Запуск бота"""
        try:
            logger.info(f"Запуск VK бота {self.bot_model.name}")
            self.is_running = True
            
            # Запускаем основной цикл
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Ошибка запуска VK бота: {e}")
            raise
    
    async def stop(self):
        """Остановка бота"""
        try:
            self.is_running = False
            logger.info(f"VK бот {self.bot_model.name} остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки VK бота: {e}")
    
    async def _main_loop(self):
        """Основной цикл обработки событий"""
        while self.is_running:
            try:
                for event in self.longpoll.listen():
                    if not self.is_running:
                        break
                    
                    await self._handle_event(event)
                    
            except Exception as e:
                logger.error(f"Ошибка в основном цикле VK бота: {e}")
                await asyncio.sleep(5)  # Пауза перед повторной попыткой
    
    async def _handle_event(self, event):
        """Обработка события VK"""
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                await self._handle_message(event.object.message)
            elif event.type == VkBotEventType.GROUP_JOIN:
                await self._handle_group_join(event.object)
            elif event.type == VkBotEventType.GROUP_LEAVE:
                await self._handle_group_leave(event.object)
                
        except Exception as e:
            logger.error(f"Ошибка обработки события VK: {e}")
    
    async def _handle_message(self, message):
        """Обработка сообщения"""
        try:
            # Игнорируем сообщения от ботов
            if message.get('from_id') < 0:
                return
            
            user_id = message.get('from_id')
            peer_id = message.get('peer_id')
            text = message.get('text', '').strip()
            
            # Получаем конфигурацию для этого чата
            chat_id = str(peer_id)
            config = self._get_chat_config(chat_id)
            
            if not config:
                # Создаем конфигурацию если её нет
                self._ensure_chat_config(chat_id, "VK Chat")
                config = self._get_chat_config(chat_id)
            
            # Проверяем команды
            if text.startswith('/'):
                await self._handle_command(text, peer_id, config)
                return
            
            # Проверяем автоответы
            if config and config.responses:
                response = self._check_auto_response(text, config.responses)
                if response:
                    await self._send_message(peer_id, response)
                    return
            
            # Проверяем фильтры
            if config and config.filters and self._should_filter_message(text, config.filters):
                # В VK API нет возможности удалить сообщение, только предупреждаем
                await self._send_message(peer_id, "Сообщение заблокировано фильтром.")
                return
            
            # Обновляем статистику
            self._update_message_count(chat_id)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения VK: {e}")
    
    async def _handle_command(self, text: str, peer_id: int, config):
        """Обработка команд"""
        try:
            command_parts = text[1:].split()
            command = command_parts[0].lower()
            args = command_parts[1:] if len(command_parts) > 1 else []
            
            if command in self.commands:
                await self.commands[command](peer_id, args, config)
            else:
                await self._send_message(peer_id, f"Неизвестная команда: /{command}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки команды VK: {e}")
    
    async def _start_command(self, peer_id: int, args: list, config):
        """Команда /start"""
        if config and config.welcome_message:
            welcome_msg = config.welcome_message
        else:
            welcome_msg = f"Привет! Я бот {self.bot_model.name}. Используйте /help для получения справки."
        
        await self._send_message(peer_id, welcome_msg)
    
    async def _help_command(self, peer_id: int, args: list, config):
        """Команда /help"""
        help_text = "Доступные команды:\n"
        help_text += "/start - Начать работу с ботом\n"
        help_text += "/help - Показать эту справку\n"
        help_text += "/settings - Настройки бота\n"
        help_text += "/ping - Проверить задержку\n"
        
        # Добавляем кастомные команды
        if config and config.commands:
            for cmd, desc in config.commands.items():
                help_text += f"/{cmd} - {desc}\n"
        
        await self._send_message(peer_id, help_text)
    
    async def _settings_command(self, peer_id: int, args: list, config):
        """Команда /settings"""
        if not config:
            await self._send_message(peer_id, "Настройки не найдены для этого чата.")
            return
        
        settings_text = f"Настройки бота для чата:\n\n"
        settings_text += f"Приветственное сообщение: {config.welcome_message or 'Не задано'}\n"
        settings_text += f"Тип чата: {config.chat_type or 'Не определен'}\n"
        settings_text += f"Сообщений обработано: {config.message_count}\n"
        
        await self._send_message(peer_id, settings_text)
    
    async def _ping_command(self, peer_id: int, args: list, config):
        """Команда /ping"""
        await self._send_message(peer_id, "🏓 Pong! Бот работает!")
    
    async def _handle_group_join(self, event):
        """Обработка присоединения к группе"""
        try:
            user_id = event.get('user_id')
            if user_id:
                # Отправляем приветственное сообщение
                welcome_msg = f"Добро пожаловать в группу! Я бот {self.bot_model.name}."
                await self._send_message(user_id, welcome_msg)
                
        except Exception as e:
            logger.error(f"Ошибка обработки присоединения к группе: {e}")
    
    async def _handle_group_leave(self, event):
        """Обработка выхода из группы"""
        try:
            user_id = event.get('user_id')
            if user_id:
                logger.info(f"Пользователь {user_id} покинул группу")
                
        except Exception as e:
            logger.error(f"Ошибка обработки выхода из группы: {e}")
    
    async def _send_message(self, peer_id: int, text: str):
        """Отправка сообщения"""
        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=text,
                random_id=0
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения VK: {e}")
    
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
                chat_type="group"
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
    
    async def send_message_to_all(self, message: str):
        """Отправка сообщения всем пользователям"""
        try:
            # Получаем список всех чатов бота
            configs = self.db_session.query(BotConfig).filter(
                BotConfig.bot_id == self.bot_model.id
            ).all()
            
            for config in configs:
                try:
                    chat_id = int(config.chat_id)
                    await self._send_message(chat_id, message)
                    await asyncio.sleep(0.1)  # Небольшая пауза между отправками
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения в чат {config.chat_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка массовой отправки сообщений: {e}")
    
    def get_group_info(self):
        """Получение информации о группе"""
        try:
            group_info = self.vk.groups.getById()
            return group_info[0] if group_info else None
        except Exception as e:
            logger.error(f"Ошибка получения информации о группе: {e}")
            return None
    
    def get_group_members_count(self):
        """Получение количества участников группы"""
        try:
            members_count = self.vk.groups.getMembers(group_id=self.bot_model.group_id)
            return members_count.get('count', 0)
        except Exception as e:
            logger.error(f"Ошибка получения количества участников: {e}")
            return 0