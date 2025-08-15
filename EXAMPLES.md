# 📚 Примеры использования Bot Platform

## 🎯 Сценарии использования

### 1. Бот поддержки клиентов
**Цель**: Автоматизация ответов на частые вопросы

**Настройки**:
```json
{
  "welcome_message": "Добро пожаловать в службу поддержки! Чем могу помочь?",
  "auto_responses": {
    "часы работы": "Мы работаем Пн-Пт с 9:00 до 18:00",
    "контакты": "Наш email: support@company.com, телефон: +7-999-123-45-67",
    "доставка": "Доставка осуществляется в течение 1-3 дней",
    "возврат": "Возврат товара возможен в течение 14 дней"
  },
  "working_hours": "Пн-Пт 9:00-18:00"
}
```

**Результат**: Бот автоматически отвечает на стандартные вопросы, освобождая время операторов.

### 2. Модератор чата
**Цель**: Автоматическая модерация сообщений

**Настройки**:
```json
{
  "filters": {
    "blocked_words": ["спам", "реклама", "оскорбления", "спойлеры"],
    "auto_delete": true,
    "warn_threshold": 3,
    "mute_duration": 3600
  },
  "commands": {
    "warn": "Предупреждение пользователя",
    "mute": "Заглушить пользователя на время",
    "ban": "Забанить пользователя"
  }
}
```

**Результат**: Бот автоматически удаляет нежелательный контент и предупреждает нарушителей.

### 3. Информационный бот
**Цель**: Распространение новостей и информации

**Настройки**:
```json
{
  "welcome_message": "Добро пожаловать! Я буду держать вас в курсе всех новостей.",
  "auto_responses": {
    "новости": "Последние новости: [ссылка на новости]",
    "расписание": "Расписание на сегодня: [ссылка на расписание]",
    "помощь": "Доступные команды: /новости, /расписание, /помощь"
  },
  "broadcast_enabled": true,
  "broadcast_schedule": "09:00, 18:00"
}
```

**Результат**: Бот автоматически отправляет новости и отвечает на запросы пользователей.

## 🛠️ Примеры настройки

### Telegram Bot

#### Базовая настройка
```python
from bot.telegram_bot import TelegramBot
from database.models import Bot, BotConfig

# Создание бота
bot = Bot(
    name="My Support Bot",
    platform="telegram",
    token="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
)

# Настройка для конкретного чата
config = BotConfig(
    bot_id=bot.id,
    chat_id="-1001234567890",
    welcome_message="Привет! Я бот поддержки.",
    auto_responses={
        "помощь": "Чем могу помочь?",
        "контакты": "Наши контакты: support@example.com"
    }
)
```

#### Расширенная настройка
```python
# Настройка фильтров
config.filters = {
    "blocked_words": ["спам", "реклама"],
    "max_message_length": 1000,
    "allow_links": False
}

# Настройка команд
config.commands = {
    "info": "Информация о компании",
    "support": "Связаться с поддержкой",
    "status": "Статус заказа"
}

# Настройка автоответов
config.responses = {
    "привет": "Здравствуйте! Чем могу помочь?",
    "спасибо": "Пожалуйста! Обращайтесь еще.",
    "до свидания": "До свидания! Хорошего дня!"
}
```

### Discord Bot

#### Настройка для сервера
```python
# Настройка для Discord сервера
discord_config = BotConfig(
    bot_id=bot.id,
    chat_id="123456789012345678",  # ID сервера
    chat_name="My Discord Server",
    chat_type="guild",
    
    # Настройки модерации
    filters={
        "blocked_words": ["спойлер", "спам"],
        "auto_delete": True,
        "warn_threshold": 2
    },
    
    # Команды модератора
    commands={
        "kick": "Кикнуть пользователя",
        "ban": "Забанить пользователя",
        "clear": "Очистить сообщения"
    }
)
```

### VK Bot

#### Настройка для группы ВКонтакте
```python
# Настройка для VK группы
vk_config = BotConfig(
    bot_id=bot.id,
    chat_id="123456789",  # ID группы
    chat_name="My VK Group",
    chat_type="group",
    
    # Настройки для VK
    welcome_message="Добро пожаловать в нашу группу!",
    auto_responses={
        "правила": "Правила группы: [ссылка на правила]",
        "контакты": "Наши контакты: [контактная информация]"
    }
)
```

## 🔄 Автоматизация

### Автоответы по расписанию
```python
import asyncio
from datetime import datetime, time

async def scheduled_broadcast(bot, chat_id, message):
    """Отправка сообщений по расписанию"""
    current_time = datetime.now().time()
    
    # Утреннее сообщение в 9:00
    if current_time.hour == 9 and current_time.minute == 0:
        await bot.send_message(chat_id, "Доброе утро! Начинаем рабочий день.")
    
    # Вечернее сообщение в 18:00
    elif current_time.hour == 18 and current_time.minute == 0:
        await bot.send_message(chat_id, "Рабочий день завершен. Хорошего вечера!")

# Запуск планировщика
async def start_scheduler():
    while True:
        await scheduled_broadcast(bot, chat_id, message)
        await asyncio.sleep(60)  # Проверяем каждую минуту
```

### Умные фильтры
```python
def smart_filter(message_text, config):
    """Умная фильтрация сообщений"""
    
    # Проверка на спам
    if is_spam(message_text):
        return "spam", "Сообщение похоже на спам"
    
    # Проверка на оскорбления
    if contains_offensive_language(message_text):
        return "offensive", "Сообщение содержит оскорбления"
    
    # Проверка на рекламу
    if is_advertisement(message_text):
        return "advertisement", "Реклама запрещена"
    
    return "ok", None

def is_spam(text):
    """Определение спама"""
    # Простая логика определения спама
    if len(text) > 1000:  # Слишком длинное сообщение
        return True
    if text.count('!') > 5:  # Много восклицательных знаков
        return True
    return False
```

## 📊 Аналитика и статистика

### Сбор статистики
```python
class BotAnalytics:
    def __init__(self, bot_id):
        self.bot_id = bot_id
    
    def track_message(self, chat_id, user_id, message_type):
        """Отслеживание сообщений"""
        # Сохранение в базу данных
        message_record = MessageRecord(
            bot_id=self.bot_id,
            chat_id=chat_id,
            user_id=user_id,
            message_type=message_type,
            timestamp=datetime.now()
        )
        db.add(message_record)
        db.commit()
    
    def get_chat_stats(self, chat_id):
        """Получение статистики чата"""
        stats = db.query(MessageRecord).filter(
            MessageRecord.bot_id == self.bot_id,
            MessageRecord.chat_id == chat_id
        ).all()
        
        return {
            "total_messages": len(stats),
            "unique_users": len(set(s.user_id for s in stats)),
            "message_types": self._count_message_types(stats)
        }
```

## 🎨 Кастомизация интерфейса

### Кастомные команды
```python
# Регистрация кастомных команд
async def custom_info_command(update, context):
    """Кастомная команда /info"""
    chat_id = str(update.effective_chat.id)
    config = get_bot_config(bot_id, chat_id)
    
    info_text = f"""
📋 Информация о боте:
• Название: {config.bot.name}
• Платформа: {config.bot.platform}
• Статус: {'Активен' if config.bot.is_active else 'Неактивен'}
• Сообщений обработано: {config.message_count}
• Создан: {config.created_at.strftime('%d.%m.%Y')}
    """
    
    await update.message.reply_text(info_text)

# Добавление в обработчики
application.add_handler(CommandHandler("info", custom_info_command))
```

### Интерактивные кнопки
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def show_settings_menu(update, context):
    """Показать меню настроек"""
    keyboard = [
        [InlineKeyboardButton("📝 Приветствие", callback_data="edit_welcome")],
        [InlineKeyboardButton("🤖 Автоответы", callback_data="edit_responses")],
        [InlineKeyboardButton("🚫 Фильтры", callback_data="edit_filters")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите настройку для изменения:",
        reply_markup=reply_markup
    )
```

## 🚀 Интеграция с внешними сервисами

### Webhook для внешних API
```python
from fastapi import FastAPI, Request
import requests

app = FastAPI()

@app.post("/webhook/external")
async def external_webhook(request: Request):
    """Webhook для внешних сервисов"""
    data = await request.json()
    
    # Обработка данных от внешнего сервиса
    if data.get("type") == "notification":
        chat_id = data.get("chat_id")
        message = data.get("message")
        
        # Отправка сообщения через бота
        await bot.send_message(chat_id, message)
    
    return {"status": "ok"}

# Использование
# POST /webhook/external
# {
#   "type": "notification",
#   "chat_id": "123456789",
#   "message": "Новое уведомление!"
# }
```

### Интеграция с CRM
```python
class CRMIntegration:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
    
    async def create_ticket(self, user_id, message):
        """Создание тикета в CRM"""
        ticket_data = {
            "user_id": user_id,
            "message": message,
            "source": "telegram_bot",
            "priority": "normal"
        }
        
        response = requests.post(
            f"{self.base_url}/tickets",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=ticket_data
        )
        
        return response.json()
    
    async def get_ticket_status(self, ticket_id):
        """Получение статуса тикета"""
        response = requests.get(
            f"{self.base_url}/tickets/{ticket_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        return response.json()
```

## 🔧 Расширение функциональности

### Создание плагина
```python
class BotPlugin:
    """Базовый класс для плагинов"""
    
    def __init__(self, bot):
        self.bot = bot
        self.name = "Base Plugin"
        self.version = "1.0.0"
    
    async def on_message(self, message):
        """Обработка сообщений"""
        pass
    
    async def on_command(self, command, args):
        """Обработка команд"""
        pass
    
    def get_help(self):
        """Справка по плагину"""
        return f"Плагин {self.name} версии {self.version}"

class WeatherPlugin(BotPlugin):
    """Плагин для погоды"""
    
    def __init__(self, bot, api_key):
        super().__init__(bot)
        self.name = "Weather Plugin"
        self.api_key = api_key
    
    async def on_command(self, command, args):
        if command == "weather":
            city = args[0] if args else "Москва"
            weather = await self.get_weather(city)
            return f"Погода в {city}: {weather}"
    
    async def get_weather(self, city):
        # Логика получения погоды
        return "20°C, солнечно"
```

Эти примеры показывают, как можно использовать Bot Platform для создания различных типов ботов с богатой функциональностью и возможностью кастомизации под конкретные нужды.