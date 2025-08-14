import re
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from aiogram.types import Message
from config import CONTENT_FILTERS
from database import db
from utils import escape_markdown, truncate_text

logger = logging.getLogger(__name__)

class ContentFilter:
    """Класс для фильтрации контента"""
    
    def __init__(self):
        self.bad_words_cache = {}  # Кэш запрещенных слов по чатам
        self.link_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r't\.me/[a-zA-Z0-9_]+',
            r'telegram\.me/[a-zA-Z0-9_]+'
        ]
        
    async def check_message(self, message: Message) -> Dict[str, any]:
        """Проверка сообщения на соответствие фильтрам"""
        try:
            if not message.text:
                return {'passed': True, 'violations': [], 'action': None}
            
            text = message.text
            chat_id = message.chat.id
            violations = []
            action = None
            
            # Проверка на запрещенные слова
            if CONTENT_FILTERS['bad_words']:
                bad_words_check = await self._check_bad_words(text, chat_id)
                if bad_words_check['violation']:
                    violations.append(bad_words_check['reason'])
                    action = 'warning'
            
            # Проверка на ссылки
            if CONTENT_FILTERS['links']:
                links_check = await self._check_links(text)
                if links_check['violation']:
                    violations.append(links_check['reason'])
                    action = 'mute_1'
            
            # Проверка на капс
            if CONTENT_FILTERS['caps']:
                caps_check = await self._check_caps(text)
                if caps_check['violation']:
                    violations.append(caps_check['reason'])
                    action = 'warning'
            
            # Проверка на спам эмодзи
            if CONTENT_FILTERS['emoji_spam']:
                emoji_check = await self._check_emoji_spam(text)
                if emoji_check['violation']:
                    violations.append(emoji_check['reason'])
                    action = 'warning'
            
            # Проверка на длинные сообщения
            if CONTENT_FILTERS['long_messages']:
                length_check = await self._check_message_length(text)
                if length_check['violation']:
                    violations.append(length_check['reason'])
                    action = 'warning'
            
            # Проверка на повторяющиеся символы
            if CONTENT_FILTERS['repeated_chars']:
                repeat_check = await self._check_repeated_chars(text)
                if repeat_check['violation']:
                    violations.append(repeat_check['reason'])
                    action = 'warning'
            
            # Проверка на спам числами
            if CONTENT_FILTERS['number_spam']:
                number_check = await self._check_number_spam(text)
                if number_check['violation']:
                    violations.append(number_check['reason'])
                    action = 'warning'
            
            return {
                'passed': len(violations) == 0,
                'violations': violations,
                'action': action,
                'text': text
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки фильтров: {e}")
            return {'passed': True, 'violations': [], 'action': None}
    
    async def _check_bad_words(self, text: str, chat_id: int) -> Dict[str, any]:
        """Проверка на запрещенные слова"""
        try:
            # Получаем запрещенные слова для чата
            bad_words = await self._get_bad_words(chat_id)
            
            text_lower = text.lower()
            found_words = []
            
            for word in bad_words:
                if word.lower() in text_lower:
                    found_words.append(word)
            
            if found_words:
                return {
                    'violation': True,
                    'reason': f'Запрещенные слова: {", ".join(found_words[:3])}'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки запрещенных слов: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_links(self, text: str) -> Dict[str, any]:
        """Проверка на ссылки"""
        try:
            found_links = []
            
            for pattern in self.link_patterns:
                links = re.findall(pattern, text, re.IGNORECASE)
                found_links.extend(links)
            
            if found_links:
                return {
                    'violation': True,
                    'reason': f'Обнаружены ссылки: {len(found_links)} шт.'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки ссылок: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_caps(self, text: str) -> Dict[str, any]:
        """Проверка на капс"""
        try:
            if len(text) < 10:
                return {'violation': False, 'reason': ''}
            
            # Подсчитываем процент заглавных букв
            caps_count = sum(1 for c in text if c.isupper() and c.isalpha())
            total_letters = sum(1 for c in text if c.isalpha())
            
            if total_letters == 0:
                return {'violation': False, 'reason': ''}
            
            caps_ratio = caps_count / total_letters
            
            if caps_ratio > 0.7:
                return {
                    'violation': True,
                    'reason': f'Слишком много заглавных букв: {caps_ratio:.1%}'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки капса: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_emoji_spam(self, text: str) -> Dict[str, any]:
        """Проверка на спам эмодзи"""
        try:
            # Паттерн для поиска эмодзи
            emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF]'
            emojis = re.findall(emoji_pattern, text)
            
            if len(emojis) > 5:
                return {
                    'violation': True,
                    'reason': f'Слишком много эмодзи: {len(emojis)} шт.'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки эмодзи: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_message_length(self, text: str) -> Dict[str, any]:
        """Проверка длины сообщения"""
        try:
            max_length = CONTENT_FILTERS.get('max_message_length', 1000)
            
            if len(text) > max_length:
                return {
                    'violation': True,
                    'reason': f'Сообщение слишком длинное: {len(text)} символов'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки длины сообщения: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_repeated_chars(self, text: str) -> Dict[str, any]:
        """Проверка на повторяющиеся символы"""
        try:
            if len(text) < 10:
                return {'violation': False, 'reason': ''}
            
            # Ищем повторяющиеся символы (3 и более подряд)
            for i in range(len(text) - 2):
                if text[i] == text[i+1] == text[i+2] and text[i].isalnum():
                    return {
                        'violation': True,
                        'reason': 'Повторяющиеся символы'
                    }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки повторяющихся символов: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _check_number_spam(self, text: str) -> Dict[str, any]:
        """Проверка на спам числами"""
        try:
            # Ищем последовательности чисел
            numbers = re.findall(r'\d+', text)
            
            if len(numbers) > 5:
                return {
                    'violation': True,
                    'reason': f'Слишком много чисел: {len(numbers)} шт.'
                }
            
            return {'violation': False, 'reason': ''}
            
        except Exception as e:
            logger.error(f"Ошибка проверки спама числами: {e}")
            return {'violation': False, 'reason': ''}
    
    async def _get_bad_words(self, chat_id: int) -> List[str]:
        """Получение запрещенных слов для чата"""
        try:
            # Проверяем кэш
            if chat_id in self.bad_words_cache:
                return self.bad_words_cache[chat_id]
            
            # Получаем из базы данных
            filters = db.get_filters(chat_id, 'bad_words')
            bad_words = [f['pattern'] for f in filters if f['is_active']]
            
            # Добавляем базовые слова
            base_words = ['спам', 'реклама', 'scam', 'spam', 'advertisement']
            bad_words.extend(base_words)
            
            # Кэшируем результат
            self.bad_words_cache[chat_id] = bad_words
            
            return bad_words
            
        except Exception as e:
            logger.error(f"Ошибка получения запрещенных слов: {e}")
            return ['спам', 'реклама']

class FilterManager:
    """Класс для управления фильтрами"""
    
    def __init__(self):
        self.content_filter = ContentFilter()
    
    async def add_filter(self, chat_id: int, filter_type: str, pattern: str, 
                        action: str, moderator_id: int) -> bool:
        """Добавление нового фильтра"""
        try:
            # Валидация паттерна
            if not self._validate_pattern(pattern):
                return False
            
            # Добавляем в базу данных
            success = db.add_filter(chat_id, filter_type, pattern, action, moderator_id)
            
            if success:
                # Очищаем кэш для этого чата
                if hasattr(self.content_filter, 'bad_words_cache'):
                    self.content_filter.bad_words_cache.pop(chat_id, None)
                
                logger.info(f"Фильтр добавлен: {filter_type} - {pattern}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка добавления фильтра: {e}")
            return False
    
    async def remove_filter(self, filter_id: int, moderator_id: int) -> bool:
        """Удаление фильтра"""
        try:
            success = db.remove_filter(filter_id, moderator_id)
            
            if success:
                logger.info(f"Фильтр {filter_id} удален")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка удаления фильтра: {e}")
            return False
    
    async def update_filter(self, filter_id: int, pattern: str, action: str, 
                           moderator_id: int) -> bool:
        """Обновление фильтра"""
        try:
            # Валидация паттерна
            if not self._validate_pattern(pattern):
                return False
            
            success = db.update_filter(filter_id, pattern, action, moderator_id)
            
            if success:
                logger.info(f"Фильтр {filter_id} обновлен")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка обновления фильтра: {e}")
            return False
    
    async def get_filters(self, chat_id: int, filter_type: str = None) -> List[Dict]:
        """Получение фильтров для чата"""
        try:
            return db.get_filters(chat_id, filter_type)
        except Exception as e:
            logger.error(f"Ошибка получения фильтров: {e}")
            return []
    
    async def toggle_filter(self, filter_id: int, moderator_id: int) -> bool:
        """Включение/выключение фильтра"""
        try:
            success = db.toggle_filter(filter_id, moderator_id)
            
            if success:
                logger.info(f"Фильтр {filter_id} переключен")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка переключения фильтра: {e}")
            return False
    
    def _validate_pattern(self, pattern: str) -> bool:
        """Валидация паттерна фильтра"""
        try:
            if not pattern or len(pattern) < 2:
                return False
            
            # Проверяем, что паттерн можно скомпилировать как регулярное выражение
            re.compile(pattern)
            return True
            
        except re.error:
            return False
    
    async def test_filter(self, pattern: str, test_text: str) -> Dict[str, any]:
        """Тестирование фильтра"""
        try:
            if not self._validate_pattern(pattern):
                return {
                    'valid': False,
                    'error': 'Неверный формат паттерна'
                }
            
            # Компилируем регулярное выражение
            regex = re.compile(pattern, re.IGNORECASE)
            
            # Тестируем на тексте
            matches = regex.findall(test_text)
            
            return {
                'valid': True,
                'matches': matches,
                'match_count': len(matches),
                'test_text': test_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка тестирования фильтра: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    async def get_filter_stats(self, chat_id: int) -> Dict[str, any]:
        """Получение статистики фильтров"""
        try:
            filters = await self.get_filters(chat_id)
            
            stats = {
                'total_filters': len(filters),
                'active_filters': len([f for f in filters if f['is_active']]),
                'by_type': {},
                'by_action': {}
            }
            
            for filter_item in filters:
                # Статистика по типам
                filter_type = filter_item['filter_type']
                if filter_type not in stats['by_type']:
                    stats['by_type'][filter_type] = 0
                stats['by_type'][filter_type] += 1
                
                # Статистика по действиям
                action = filter_item['action']
                if action not in stats['by_action']:
                    stats['by_action'][action] = 0
                stats['by_action'][action] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики фильтров: {e}")
            return {}

# Создаем глобальный экземпляр
filter_manager = FilterManager()