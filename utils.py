import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from aiogram.types import User

logger = logging.getLogger(__name__)

def format_time(dt: datetime) -> str:
    """Форматирование времени для отображения"""
    try:
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception as e:
        logger.error(f"Ошибка форматирования времени: {e}")
        return "Неизвестно"

def format_duration(seconds: int) -> str:
    """Форматирование длительности для отображения"""
    try:
        if seconds < 60:
            return f"{seconds} секунд"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} минут"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} часов"
        else:
            days = seconds // 86400
            return f"{days} дней"
    except Exception as e:
        logger.error(f"Ошибка форматирования длительности: {e}")
        return "Неизвестно"

def get_user_mention(user: User) -> str:
    """Получение упоминания пользователя"""
    try:
        if user.username:
            return f"@{user.username}"
        elif user.first_name:
            if user.last_name:
                return f"{user.first_name} {user.last_name}"
            else:
                return user.first_name
        else:
            return f"Пользователь {user.id}"
    except Exception as e:
        logger.error(f"Ошибка получения упоминания пользователя: {e}")
        return "Неизвестный пользователь"

def parse_duration(duration_str: str) -> int:
    """Парсинг длительности из строки"""
    try:
        duration_str = duration_str.lower().strip()
        
        # Паттерны для парсинга
        patterns = [
            (r'(\d+)\s*сек(?:унд)?', 1),
            (r'(\d+)\s*с', 1),
            (r'(\d+)\s*мин(?:ут)?', 60),
            (r'(\d+)\s*м', 60),
            (r'(\d+)\s*час(?:ов)?', 3600),
            (r'(\d+)\s*ч', 3600),
            (r'(\d+)\s*дн(?:ей)?', 86400),
            (r'(\d+)\s*д', 86400),
            (r'(\d+)\s*нед(?:ель)?', 604800),
            (r'(\d+)\s*н', 604800),
            (r'(\d+)\s*мес(?:яцев)?', 2592000),
            (r'(\d+)\s*мес', 2592000)
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, duration_str)
            if match:
                value = int(match.group(1))
                return value * multiplier
        
        # Если ничего не найдено, пробуем просто число (по умолчанию минуты)
        try:
            return int(duration_str) * 60
        except ValueError:
            return 0
            
    except Exception as e:
        logger.error(f"Ошибка парсинга длительности: {e}")
        return 0

def create_backup_filename(prefix: str = "backup") -> str:
    """Создание имени файла для резервной копии"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.json"
    except Exception as e:
        logger.error(f"Ошибка создания имени файла резервной копии: {e}")
        return f"{prefix}_{int(datetime.now().timestamp())}.json"

def validate_json(data: str) -> bool:
    """Проверка валидности JSON"""
    try:
        json.loads(data)
        return True
    except (json.JSONDecodeError, TypeError):
        return False

def safe_json_dumps(obj: object, **kwargs) -> str:
    """Безопасный JSON dump с обработкой ошибок"""
    try:
        return json.dumps(obj, ensure_ascii=False, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка JSON сериализации: {e}")
        return "{}"

def safe_json_loads(data: str, **kwargs) -> object:
    """Безопасный JSON load с обработкой ошибок"""
    try:
        return json.loads(data, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка JSON десериализации: {e}")
        return {}

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезка текста с суффиксом"""
    try:
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    except Exception as e:
        logger.error(f"Ошибка обрезки текста: {e}")
        return text

def escape_markdown(text: str) -> str:
    """Экранирование специальных символов Markdown"""
    try:
        # Символы, которые нужно экранировать в Markdown
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    except Exception as e:
        logger.error(f"Ошибка экранирования Markdown: {e}")
        return text

def format_number(num: Union[int, float]) -> str:
    """Форматирование чисел с разделителями"""
    try:
        if isinstance(num, float):
            return f"{num:,.2f}"
        else:
            return f"{num:,}"
    except Exception as e:
        logger.error(f"Ошибка форматирования числа: {e}")
        return str(num)

def get_time_ago(dt: datetime) -> str:
    """Получение относительного времени"""
    try:
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            if diff.days == 1:
                return "вчера"
            elif diff.days < 7:
                return f"{diff.days} дней назад"
            else:
                weeks = diff.days // 7
                if weeks == 1:
                    return "неделю назад"
                else:
                    return f"{weeks} недель назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            if hours == 1:
                return "час назад"
            elif hours < 5:
                return f"{hours} часа назад"
            else:
                return f"{hours} часов назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            if minutes == 1:
                return "минуту назад"
            elif minutes < 5:
                return f"{minutes} минуты назад"
            else:
                return f"{minutes} минут назад"
        else:
            return "только что"
            
    except Exception as e:
        logger.error(f"Ошибка получения относительного времени: {e}")
        return "неизвестно"

def is_valid_username(username: str) -> bool:
    """Проверка валидности username"""
    try:
        if not username:
            return False
        
        # Username должен начинаться с буквы и содержать только буквы, цифры и подчеркивания
        pattern = r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$'
        return bool(re.match(pattern, username))
    except Exception as e:
        logger.error(f"Ошибка проверки username: {e}")
        return False

def clean_html_tags(text: str) -> str:
    """Очистка HTML тегов из текста"""
    try:
        # Простое удаление HTML тегов
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)
    except Exception as e:
        logger.error(f"Ошибка очистки HTML тегов: {e}")
        return text

def extract_mentions(text: str) -> List[str]:
    """Извлечение упоминаний из текста"""
    try:
        # Ищем упоминания в формате @username
        mentions = re.findall(r'@(\w+)', text)
        return list(set(mentions))  # Убираем дубликаты
    except Exception as e:
        logger.error(f"Ошибка извлечения упоминаний: {e}")
        return []

def is_weekend(dt: datetime = None) -> bool:
    """Проверка, является ли дата выходным днем"""
    try:
        if dt is None:
            dt = datetime.now()
        return dt.weekday() >= 5  # 5 = суббота, 6 = воскресенье
    except Exception as e:
        logger.error(f"Ошибка проверки выходного дня: {e}")
        return False

def get_working_hours() -> Dict[str, int]:
    """Получение текущего времени работы"""
    try:
        now = datetime.now()
        hour = now.hour
        
        if 9 <= hour < 18:
            return {"status": "working", "hours_left": 18 - hour}
        elif hour < 9:
            return {"status": "before_work", "hours_until": 9 - hour}
        else:
            return {"status": "after_work", "hours_passed": hour - 18}
    except Exception as e:
        logger.error(f"Ошибка получения времени работы: {e}")
        return {"status": "unknown", "error": str(e)}