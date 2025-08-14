import re
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from aiogram import Bot
from aiogram.types import Message, ChatMember, User
from aiogram.exceptions import TelegramAPIError

from config import (
    MAX_WARNINGS, AUTO_DELETE_SPAM, SPAM_THRESHOLD, 
    FLOOD_PROTECTION, CONTENT_FILTERS, TEMP_BAN_DURATIONS
)
from database import db
from utils import format_time, format_duration, get_user_mention, parse_duration

logger = logging.getLogger(__name__)

class ChatModerator:
    """Класс для модерации чатов"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.user_message_counts = {}  # Счетчик сообщений пользователей
        self.user_last_message_time = {}  # Время последнего сообщения
        self.spam_detection = {}  # Детекция спама
        self.flood_protection = {}  # Защита от флуда
        
    async def check_message(self, message: Message) -> Dict[str, any]:
        """Проверка сообщения на нарушения"""
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id
            current_time = datetime.now()
            
            # Инициализация данных для чата
            if chat_id not in self.user_message_counts:
                self.user_message_counts[chat_id] = {}
            if chat_id not in self.user_last_message_time:
                self.user_last_message_time[chat_id] = {}
            if chat_id not in self.spam_detection:
                self.spam_detection[chat_id] = {}
            if chat_id not in self.flood_protection:
                self.flood_protection[chat_id] = {}
            
            violations = []
            action_needed = False
            action_type = None
            duration = 0
            
            # Проверка на флуд
            if FLOOD_PROTECTION:
                flood_check = await self._check_flood(chat_id, user_id, current_time)
                if flood_check['violation']:
                    violations.append(flood_check['reason'])
                    action_needed = True
                    action_type = 'mute_1'
                    duration = TEMP_BAN_DURATIONS['mute_1']
            
            # Проверка на спам
            if AUTO_DELETE_SPAM:
                spam_check = await self._check_spam(chat_id, user_id, current_time)
                if spam_check['violation']:
                    violations.append(spam_check['reason'])
                    action_needed = True
                    action_type = 'mute_2'
                    duration = TEMP_BAN_DURATIONS['mute_2']
            
            # Проверка контента
            content_check = await self._check_content(message)
            if content_check['violation']:
                violations.append(content_check['reason'])
                action_needed = True
                action_type = content_check['action_type']
                duration = content_check['duration']
            
            # Проверка количества предупреждений
            warnings_check = await self._check_warnings(chat_id, user_id)
            if warnings_check['violation']:
                violations.append(warnings_check['reason'])
                action_needed = True
                action_type = 'ban_1'
                duration = TEMP_BAN_DURATIONS['ban_1']
            
            return {
                'violations': violations,
                'action_needed': action_needed,
                'action_type': action_type,
                'duration': duration,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки сообщения: {e}")
            return {
                'violations': [],
                'action_needed': False,
                'action_type': None,
                'duration': 0,
                'message': message
            }
    
    async def _check_flood(self, chat_id: int, user_id: int, current_time: datetime) -> Dict[str, any]:
        """Проверка на флуд"""
        try:
            if user_id not in self.user_last_message_time[chat_id]:
                self.user_last_message_time[chat_id][user_id] = current_time
                return {'violation': False, 'reason': ''}
            
            last_time = self.user_last_message_time[chat_id][user_id]
            time_diff = (current_time - last_time).total_seconds()
            
            # Если сообщения идут чаще чем раз в 2 секунды
            if time_diff < 2:
                self.user_last_message_time[chat_id][user_id] = current_time
                return {
                    'violation': True, 
                    'reason': 'Флуд: слишком частые сообщения'
                }
            
            self.user_last_message_time[chat_id][user_id] = current_time
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки флуда: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_spam(self, chat_id: int, user_id: int, current_time: datetime) -> Dict[str, any]:
        """Проверка на спам"""
        try:
            if user_id not in self.spam_detection[chat_id]:
                self.spam_detection[chat_id][user_id] = {
                    'count': 0,
                    'first_message': current_time
                }
            
            spam_data = self.spam_detection[chat_id][user_id]
            spam_data['count'] += 1
            
            # Проверяем количество сообщений за последнюю минуту
            time_diff = (current_time - spam_data['first_message']).total_seconds()
            
            if time_diff > 60:  # Сброс счетчика каждую минуту
                spam_data['count'] = 1
                spam_data['first_message'] = current_time
            elif spam_data['count'] > SPAM_THRESHOLD:
                return {
                    'violation': True,
                    'reason': f'Спам: {spam_data["count"]} сообщений за минуту'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки спама: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_content(self, message: Message) -> Dict[str, any]:
        """Проверка контента сообщения"""
        try:
            violations = []
            action_type = None
            duration = 0
            
            if not message.text:
                return {'violation': False, 'reason': '', 'action_type': None, 'duration': 0}
            
            text = message.text.lower()
            
            # Проверка на плохие слова
            if CONTENT_FILTERS['bad_words']:
                bad_words = await self._get_bad_words(message.chat.id)
                for word in bad_words:
                    if word.lower() in text:
                        violations.append(f'Запрещенное слово: {word}')
                        action_type = 'warning'
                        duration = TEMP_BAN_DURATIONS['warning']
                        break
            
            # Проверка на капс
            if CONTENT_FILTERS['caps']:
                caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
                if caps_ratio > 0.7 and len(text) > 10:
                    violations.append('Слишком много заглавных букв')
                    action_type = 'warning'
                    duration = TEMP_BAN_DURATIONS['warning']
            
            # Проверка на спам эмодзи
            if CONTENT_FILTERS['emoji_spam']:
                emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]', text))
                if emoji_count > 5:
                    violations.append('Слишком много эмодзи')
                    action_type = 'warning'
                    duration = TEMP_BAN_DURATIONS['warning']
            
            # Проверка на ссылки
            if CONTENT_FILTERS['links']:
                links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
                if links:
                    violations.append('Запрещены ссылки')
                    action_type = 'mute_1'
                    duration = TEMP_BAN_DURATIONS['mute_1']
            
            if violations:
                return {
                    'violation': True,
                    'reason': '; '.join(violations),
                    'action_type': action_type,
                    'duration': duration
                }
            
            return {'violation': False, 'reason': '', 'action_type': None, 'duration': 0}
            
        except Exception as e:
            logger.error(f"Ошибка проверки контента: {e}")
            return {'violation': False, 'reason': '', 'action_type': None, 'duration': 0}
    
    async def _check_warnings(self, chat_id: int, user_id: int) -> Dict[str, any]:
        """Проверка количества предупреждений"""
        try:
            user = db.get_user(user_id)
            if user and user['warnings'] >= MAX_WARNINGS:
                return {
                    'violation': True,
                    'reason': f'Превышен лимит предупреждений: {user["warnings"]}/{MAX_WARNINGS}'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки предупреждений: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _get_bad_words(self, chat_id: int) -> List[str]:
        """Получение списка запрещенных слов для чата"""
        try:
            # Здесь можно добавить логику получения запрещенных слов из базы
            # Пока возвращаем базовый список
            return ['спам', 'реклама', 'scam', 'spam']
        except Exception as e:
            logger.error(f"Ошибка получения запрещенных слов: {e}")
            return []
    
    async def apply_moderation_action(self, chat_id: int, user_id: int, action_type: str, 
                                    reason: str, moderator_id: int, duration: int = 0) -> bool:
        """Применение действия модерации"""
        try:
            # Логируем действие
            db.add_moderation_action(chat_id, user_id, action_type, reason, moderator_id, duration)
            
            # Применяем действие в зависимости от типа
            if action_type == 'warning':
                return await self._apply_warning(chat_id, user_id, reason)
            elif action_type.startswith('mute'):
                return await self._apply_mute(chat_id, user_id, reason, duration)
            elif action_type.startswith('ban'):
                return await self._apply_ban(chat_id, user_id, reason, duration)
            else:
                logger.warning(f"Неизвестный тип действия модерации: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка применения действия модерации: {e}")
            return False
    
    async def _apply_warning(self, chat_id: int, user_id: int, reason: str) -> bool:
        """Применение предупреждения"""
        try:
            # Увеличиваем счетчик предупреждений
            user = db.get_user(user_id)
            if user:
                warnings = user.get('warnings', 0) + 1
                # Обновляем пользователя в базе
                # db.update_user_warnings(user_id, warnings)
            
            # Отправляем уведомление пользователю
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"⚠️ Вы получили предупреждение в чате!\n\nПричина: {reason}\n\nБудьте внимательны к правилам чата."
                )
            except TelegramAPIError:
                logger.warning(f"Не удалось отправить уведомление пользователю {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка применения предупреждения: {e}")
            return False
    
    async def _apply_mute(self, chat_id: int, user_id: int, reason: str, duration: int) -> bool:
        """Применение мута"""
        try:
            # Добавляем временный бан
            db.add_temp_ban(chat_id, user_id, 'mute', reason, 0, duration)
            
            # Отправляем уведомление в чат
            duration_text = format_duration(duration)
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 Пользователь {get_user_mention(user_id)} получил мут на {duration_text}\n\nПричина: {reason}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка применения мута: {e}")
            return False
    
    async def _apply_ban(self, chat_id: int, user_id: int, reason: str, duration: int) -> bool:
        """Применение бана"""
        try:
            # Добавляем временный бан
            db.add_temp_ban(chat_id, user_id, 'ban', reason, 0, duration)
            
            # Отправляем уведомление в чат
            duration_text = format_duration(duration)
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 Пользователь {get_user_mention(user_id)} заблокирован на {duration_text}\n\nПричина: {reason}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка применения бана: {e}")
            return False
    
    async def check_and_expire_bans(self) -> int:
        """Проверка и истечение временных банов"""
        try:
            expired_count = db.expire_temp_bans()
            if expired_count > 0:
                logger.info(f"Истекло {expired_count} временных банов")
            return expired_count
        except Exception as e:
            logger.error(f"Ошибка проверки временных банов: {e}")
            return 0
    
    async def get_user_moderation_status(self, chat_id: int, user_id: int) -> Dict[str, any]:
        """Получение статуса модерации пользователя"""
        try:
            user = db.get_user(user_id)
            active_bans = db.get_active_temp_bans(chat_id)
            
            user_bans = [ban for ban in active_bans if ban['user_id'] == user_id]
            
            return {
                'user': user,
                'active_bans': user_bans,
                'warnings': user.get('warnings', 0) if user else 0,
                'is_banned': bool(user_bans),
                'ban_until': user_bans[0]['ban_until'] if user_bans else None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса модерации: {e}")
            return {
                'user': None,
                'active_bans': [],
                'warnings': 0,
                'is_banned': False,
                'ban_until': None
            }
    
    async def cleanup_old_data(self) -> int:
        """Очистка старых данных"""
        try:
            cleaned_count = db.cleanup_old_data()
            if cleaned_count > 0:
                logger.info(f"Очищено {cleaned_count} старых записей")
            return cleaned_count
        except Exception as e:
            logger.error(f"Ошибка очистки старых данных: {e}")
            return 0