import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Основные настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'your_bot_username')

# Настройки администратора
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID', 0))

# Настройки базы данных
DATABASE_PATH = 'chat_moderator.db'

# Настройки логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'bot.log'

# Настройки модерации
MAX_WARNINGS = 3  # Максимальное количество предупреждений
AUTO_DELETE_SPAM = True  # Автоматическое удаление спама
SPAM_THRESHOLD = 5  # Порог для определения спама (сообщений в секунду)
FLOOD_PROTECTION = True  # Защита от флуда

# Настройки уведомлений
NOTIFY_ADMINS_ON_ACTION = True  # Уведомлять админов о действиях
NOTIFY_USER_ON_WARNING = True  # Уведомлять пользователя о предупреждении

# Настройки автоматической модерации
AUTO_MODERATION = True  # Автоматическая модерация
SCAN_INTERVAL = 60  # Интервал сканирования в секундах

# Фильтры контента
CONTENT_FILTERS = {
    'bad_words': True,  # Фильтр плохих слов
    'links': True,  # Фильтр ссылок
    'media': True,  # Фильтр медиа
    'caps': True,  # Фильтр капса
    'emoji_spam': True,  # Фильтр спама эмодзи
}

# Настройки временных банов
TEMP_BAN_DURATIONS = {
    'warning': 0,  # Предупреждение
    'mute_1': 300,  # Мут на 5 минут
    'mute_2': 900,  # Мут на 15 минут
    'mute_3': 3600,  # Мут на 1 час
    'ban_1': 86400,  # Бан на 1 день
    'ban_2': 604800,  # Бан на 1 неделю
    'ban_3': 2592000,  # Бан на 1 месяц
}

# Настройки статистики
STATS_UPDATE_INTERVAL = 300  # Обновление статистики каждые 5 минут
SAVE_STATS_HISTORY = True  # Сохранять историю статистики

# Настройки резервного копирования
BACKUP_ENABLED = True
BACKUP_INTERVAL = 86400  # Резервное копирование раз в день
BACKUP_PATH = 'backups/'

# Настройки API
TELEGRAM_API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1

# Настройки безопасности
RATE_LIMIT = 10  # Максимум запросов в минуту
BLOCKED_USERS_FILE = 'blocked_users.json'
WHITELIST_FILE = 'whitelist.json'