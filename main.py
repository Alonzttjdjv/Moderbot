import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ChatMember, User, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError

from config import (
    BOT_TOKEN, ADMIN_IDS, DATABASE_PATH, LOG_LEVEL, 
    MAX_WARNINGS, AUTO_DELETE_SPAM, SPAM_THRESHOLD
)
from database import DatabaseManager
from moderator import ChatModerator
from filters import filter_manager
from utils import (
    format_time, format_duration, get_user_mention, 
    parse_duration, escape_markdown, get_time_ago
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = DatabaseManager()

# Инициализация модератора
moderator = ChatModerator(bot)

# Состояния для FSM
class ModerationStates(StatesGroup):
    waiting_for_filter_pattern = State()
    waiting_for_filter_action = State()
    waiting_for_ban_duration = State()
    waiting_for_mute_duration = State()
    waiting_for_warning_reason = State()

# Команды для администраторов
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Добавляем пользователя в базу
        user = message.from_user
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Если это личный чат, показываем информацию о боте
        if message.chat.type == "private":
            await message.answer(
                "🤖 **Бот-модератор чатов**\n\n"
                "Я помогу вам модерировать ваши чаты и группы.\n\n"
                "**Основные возможности:**\n"
                "• Автоматическая модерация контента\n"
                "• Защита от спама и флуда\n"
                "• Система предупреждений и банов\n"
                "• Настраиваемые фильтры\n"
                "• Подробная статистика\n\n"
                "**Для использования:**\n"
                "1. Добавьте меня в ваш чат\n"
                "2. Сделайте администратором\n"
                "3. Настройте параметры модерации\n\n"
                "**Команды администратора:**\n"
                "/settings - Настройки чата\n"
                "/stats - Статистика\n"
                "/filters - Управление фильтрами\n"
                "/moderate - Панель модерации",
                parse_mode="Markdown"
            )
        else:
            # В групповом чате показываем краткую информацию
            await message.answer(
                "🤖 Бот-модератор активирован!\n\n"
                "Используйте /help для просмотра команд."
            )
            
            # Добавляем чат в базу
            admins = await get_chat_admins(chat_id)
            db.add_chat(
                chat_id=chat_id,
                chat_title=message.chat.title or "Группа",
                chat_type=message.chat.type,
                admin_ids=admins
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде start: {e}")
        await message.answer("Произошла ошибка при запуске бота.")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        is_admin = await check_admin_rights(chat_id, user_id)
        
        if is_admin:
            help_text = (
                "🔧 **Команды администратора:**\n\n"
                "**Основные команды:**\n"
                "/settings - Настройки модерации\n"
                "/stats - Статистика чата\n"
                "/filters - Управление фильтрами\n"
                "/moderate - Панель модерации\n\n"
                "**Модерация:**\n"
                "/warn @username - Предупреждение\n"
                "/mute @username [время] - Мут\n"
                "/ban @username [время] - Бан\n"
                "/unban @username - Разбан\n"
                "/unmute @username - Размут\n\n"
                "**Фильтры:**\n"
                "/addfilter - Добавить фильтр\n"
                "/delfilter - Удалить фильтр\n"
                "/listfilters - Список фильтров\n\n"
                "**Статистика:**\n"
                "/userstats @username - Статистика пользователя\n"
                "/chatstats - Статистика чата\n"
                "/modstats - Статистика модерации"
            )
        else:
            help_text = (
                "📚 **Доступные команды:**\n\n"
                "/help - Показать эту справку\n"
                "/rules - Правила чата\n"
                "/report @username - Пожаловаться на пользователя"
            )
        
        await message.answer(help_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде help: {e}")
        await message.answer("Произошла ошибка при показе справки.")

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Обработчик команды /settings"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для изменения настроек.")
            return
        
        # Получаем текущие настройки
        chat = db.get_chat(chat_id)
        if not chat:
            await message.answer("❌ Чат не найден в базе данных.")
            return
        
        settings = chat.get('settings', {})
        
        # Создаем клавиатуру с настройками
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🛡️ Автомодерация: {'✅' if settings.get('auto_moderation', True) else '❌'}",
                    callback_data=f"setting_auto_moderation"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🚫 Антиспам: {'✅' if settings.get('anti_spam', True) else '❌'}",
                    callback_data=f"setting_anti_spam"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🌊 Антифлуд: {'✅' if settings.get('anti_flood', True) else '❌'}",
                    callback_data=f"setting_anti_flood"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔤 Фильтр капса: {'✅' if settings.get('caps_filter', True) else '❌'}",
                    callback_data=f"setting_caps_filter"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"😀 Фильтр эмодзи: {'✅' if settings.get('emoji_filter', True) else '❌'}",
                    callback_data=f"setting_emoji_filter"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔗 Фильтр ссылок: {'✅' if settings.get('links_filter', True) else '❌'}",
                    callback_data=f"setting_links_filter"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Дополнительные настройки",
                    callback_data="settings_advanced"
                )
            ]
        ])
        
        await message.answer(
            "⚙️ **Настройки модерации**\n\n"
            "Выберите параметр для изменения:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде settings: {e}")
        await message.answer("Произошла ошибка при показе настроек.")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для просмотра статистики.")
            return
        
        # Получаем статистику
        stats = await get_chat_statistics(chat_id)
        
        stats_text = (
            "📊 **Статистика чата**\n\n"
            f"**Общая информация:**\n"
            f"• Всего сообщений: {stats['total_messages']:,}\n"
            f"• Участников: {stats['total_users']:,}\n"
            f"• Новых участников сегодня: {stats['new_users_today']:,}\n\n"
            f"**Модерация:**\n"
            f"• Предупреждений: {stats['total_warnings']:,}\n"
            f"• Мутов: {stats['total_mutes']:,}\n"
            f"• Банов: {stats['total_bans']:,}\n"
            f"• Удаленных сообщений: {stats['deleted_messages']:,}\n\n"
            f"**Активность:**\n"
            f"• Сообщений сегодня: {stats['messages_today']:,}\n"
            f"• Активных пользователей: {stats['active_users']:,}\n"
            f"• Время последней активности: {stats['last_activity']}"
        )
        
        await message.answer(stats_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде stats: {e}")
        await message.answer("Произошла ошибка при получении статистики.")

@dp.message(Command("filters"))
async def cmd_filters(message: Message):
    """Обработчик команды /filters"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для управления фильтрами.")
            return
        
        # Получаем список фильтров
        filters = await filter_manager.get_filters(chat_id)
        
        if not filters:
            await message.answer(
                "🔍 **Фильтры**\n\n"
                "В этом чате пока нет настроенных фильтров.\n\n"
                "Используйте /addfilter для добавления нового фильтра."
            )
            return
        
        # Создаем клавиатуру с фильтрами
        keyboard_buttons = []
        for filter_item in filters[:10]:  # Показываем первые 10
            status = "✅" if filter_item['is_active'] else "❌"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {filter_item['filter_type']}: {filter_item['pattern'][:20]}...",
                    callback_data=f"filter_{filter_item['id']}"
                )
            ])
        
        # Добавляем кнопки управления
        keyboard_buttons.extend([
            [
                InlineKeyboardButton(
                    text="➕ Добавить фильтр",
                    callback_data="filter_add"
                ),
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="filter_stats"
                )
            ]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            f"🔍 **Фильтры**\n\n"
            f"Всего фильтров: {len(filters)}\n"
            f"Активных: {len([f for f in filters if f['is_active']])}\n\n"
            f"Выберите фильтр для управления:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде filters: {e}")
        await message.answer("Произошла ошибка при показе фильтров.")

@dp.message(Command("moderate"))
async def cmd_moderate(message: Message):
    """Обработчик команды /moderate"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для доступа к панели модерации.")
            return
        
        # Создаем клавиатуру модерации
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ Предупреждение",
                    callback_data="mod_action_warn"
                ),
                InlineKeyboardButton(
                    text="🔇 Мут",
                    callback_data="mod_action_mute"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Бан",
                    callback_data="mod_action_ban"
                ),
                InlineKeyboardButton(
                    text="✅ Разбан/Размут",
                    callback_data="mod_action_unban"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика модерации",
                    callback_data="mod_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧹 Очистка чата",
                    callback_data="mod_cleanup"
                )
            ]
        ])
        
        await message.answer(
            "🛡️ **Панель модерации**\n\n"
            "Выберите действие:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде moderate: {e}")
        await message.answer("Произошла ошибка при открытии панели модерации.")

# Обработчики модерации
@dp.message(Command("warn"))
async def cmd_warn(message: Message):
    """Обработчик команды /warn"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для выдачи предупреждений.")
            return
        
        # Парсим команду
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ Неверный формат команды.\n"
                "Используйте: /warn @username [причина]"
            )
            return
        
        # Получаем username и причину
        target_username = args[1].lstrip('@')
        reason = ' '.join(args[2:]) if len(args) > 2 else "Нарушение правил чата"
        
        # Находим пользователя
        target_user = await find_user_by_username(chat_id, target_username)
        if not target_user:
            await message.answer("❌ Пользователь не найден.")
            return
        
        # Применяем предупреждение
        success = await moderator.apply_moderation_action(
            chat_id=chat_id,
            user_id=target_user['user_id'],
            action_type='warning',
            reason=reason,
            moderator_id=user_id
        )
        
        if success:
            await message.answer(
                f"⚠️ Пользователь {get_user_mention(target_user)} получил предупреждение.\n\n"
                f"Причина: {reason}"
            )
        else:
            await message.answer("❌ Ошибка при выдаче предупреждения.")
        
    except Exception as e:
        logger.error(f"Ошибка в команде warn: {e}")
        await message.answer("Произошла ошибка при выдаче предупреждения.")

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    """Обработчик команды /mute"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для выдачи мутов.")
            return
        
        # Парсим команду
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ Неверный формат команды.\n"
                "Используйте: /mute @username [время] [причина]"
            )
            return
        
        # Получаем username, время и причину
        target_username = args[1].lstrip('@')
        duration_str = args[2] if len(args) > 2 and not args[2].startswith('@') else "1ч"
        reason = ' '.join(args[3:]) if len(args) > 3 else "Нарушение правил чата"
        
        # Парсим длительность
        duration = parse_duration(duration_str)
        if duration == 0:
            duration = 3600  # По умолчанию 1 час
        
        # Находим пользователя
        target_user = await find_user_by_username(chat_id, target_username)
        if not target_user:
            await message.answer("❌ Пользователь не найден.")
            return
        
        # Применяем мут
        success = await moderator.apply_moderation_action(
            chat_id=chat_id,
            user_id=target_user['user_id'],
            action_type='mute_1',
            reason=reason,
            moderator_id=user_id,
            duration=duration
        )
        
        if success:
            duration_text = format_duration(duration)
            await message.answer(
                f"🔇 Пользователь {get_user_mention(target_user)} получил мут на {duration_text}.\n\n"
                f"Причина: {reason}"
            )
        else:
            await message.answer("❌ Ошибка при выдаче мута.")
        
    except Exception as e:
        logger.error(f"Ошибка в команде mute: {e}")
        await message.answer("Произошла ошибка при выдаче мута.")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    """Обработчик команды /ban"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем права администратора
        if not await check_admin_rights(chat_id, user_id):
            await message.answer("❌ У вас нет прав для выдачи банов.")
            return
        
        # Парсим команду
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ Неверный формат команды.\n"
                "Используйте: /ban @username [время] [причина]"
            )
            return
        
        # Получаем username, время и причину
        target_username = args[1].lstrip('@')
        duration_str = args[2] if len(args) > 2 and not args[2].startswith('@') else "1д"
        reason = ' '.join(args[3:]) if len(args) > 3 else "Нарушение правил чата"
        
        # Парсим длительность
        duration = parse_duration(duration_str)
        if duration == 0:
            duration = 86400  # По умолчанию 1 день
        
        # Находим пользователя
        target_user = await find_user_by_username(chat_id, target_username)
        if not target_user:
            await message.answer("❌ Пользователь не найден.")
            return
        
        # Применяем бан
        success = await moderator.apply_moderation_action(
            chat_id=chat_id,
            user_id=target_user['user_id'],
            action_type='ban_1',
            reason=reason,
            moderator_id=user_id,
            duration=duration
        )
        
        if success:
            duration_text = format_duration(duration)
            await message.answer(
                f"🚫 Пользователь {get_user_mention(target_user)} заблокирован на {duration_text}.\n\n"
                f"Причина: {reason}"
            )
        else:
            await message.answer("❌ Ошибка при выдаче бана.")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ban: {e}")
        await message.answer("Произошла ошибка при выдаче бана.")

# Обработчик всех сообщений для модерации
@dp.message()
async def handle_message(message: Message):
    """Обработчик всех сообщений"""
    try:
        # Игнорируем сообщения от ботов
        if message.from_user.is_bot:
            return
        
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Добавляем пользователя в базу
        user = message.from_user
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Логируем сообщение
        db.add_message(
            chat_id=chat_id,
            user_id=user_id,
            message_id=message.message_id,
            message_type=message.content_type,
            content=message.text or message.caption or ""
        )
        
        # Проверяем сообщение на нарушения
        check_result = await moderator.check_message(message)
        
        if check_result['action_needed']:
            # Применяем действие модерации
            await moderator.apply_moderation_action(
                chat_id=chat_id,
                user_id=user_id,
                action_type=check_result['action_type'],
                reason='; '.join(check_result['violations']),
                moderator_id=0,  # Система
                duration=check_result['duration']
            )
            
            # Удаляем нарушающее сообщение
            try:
                await message.delete()
            except TelegramAPIError:
                logger.warning(f"Не удалось удалить сообщение {message.message_id}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# Вспомогательные функции
async def check_admin_rights(chat_id: int, user_id: int) -> bool:
    """Проверка прав администратора"""
    try:
        # Проверяем в базе данных
        chat = db.get_chat(chat_id)
        if chat and user_id in chat.get('admin_ids', []):
            return True
        
        # Проверяем через Telegram API
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
        
    except Exception as e:
        logger.error(f"Ошибка проверки прав администратора: {e}")
        return False

async def get_chat_admins(chat_id: int) -> List[int]:
    """Получение списка администраторов чата"""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return [admin.user.id for admin in admins]
    except Exception as e:
        logger.error(f"Ошибка получения администраторов: {e}")
        return []

async def find_user_by_username(chat_id: int, username: str) -> Optional[Dict]:
    """Поиск пользователя по username"""
    try:
        # Ищем в базе данных
        users = db.search_users_by_username(username)
        if users:
            return users[0]
        
        # Если не найдено, возвращаем None
        return None
        
    except Exception as e:
        logger.error(f"Ошибка поиска пользователя: {e}")
        return None

async def get_chat_statistics(chat_id: int) -> Dict:
    """Получение статистики чата"""
    try:
        stats = db.get_chat_statistics(chat_id)
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {
            'total_messages': 0,
            'total_users': 0,
            'new_users_today': 0,
            'total_warnings': 0,
            'total_mutes': 0,
            'total_bans': 0,
            'deleted_messages': 0,
            'messages_today': 0,
            'active_users': 0,
            'last_activity': 'Неизвестно'
        }

# Периодические задачи
async def periodic_tasks():
    """Выполнение периодических задач"""
    while True:
        try:
            # Проверяем истечение временных банов
            expired_bans = await moderator.check_and_expire_bans()
            if expired_bans > 0:
                logger.info(f"Истекло {expired_bans} временных банов")
            
            # Очищаем старые данные
            cleaned_data = await moderator.cleanup_old_data()
            if cleaned_data > 0:
                logger.info(f"Очищено {cleaned_data} старых записей")
            
            # Ждем 5 минут
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Ошибка в периодических задачах: {e}")
            await asyncio.sleep(60)

# Обработчики callback-запросов
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    """Обработчик callback-запросов"""
    try:
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        
        # Проверяем права администратора для большинства действий
        if not await check_admin_rights(chat_id, user_id):
            await callback.answer("❌ У вас нет прав для этого действия.")
            return
        
        if data.startswith("setting_"):
            await handle_setting_callback(callback, data)
        elif data.startswith("filter_"):
            await handle_filter_callback(callback, data)
        elif data.startswith("mod_action_"):
            await handle_mod_action_callback(callback, data)
        elif data.startswith("mod_"):
            await handle_mod_callback(callback, data)
        else:
            await callback.answer("Неизвестное действие")
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        await callback.answer("Произошла ошибка")

async def handle_setting_callback(callback: types.CallbackQuery, data: str):
    """Обработка callback для настроек"""
    try:
        setting_name = data.replace("setting_", "")
        chat_id = callback.message.chat.id
        
        # Получаем текущие настройки
        chat = db.get_chat(chat_id)
        if not chat:
            await callback.answer("❌ Чат не найден")
            return
        
        settings = chat.get('settings', {})
        current_value = settings.get(setting_name, True)
        
        # Инвертируем значение
        settings[setting_name] = not current_value
        
        # Обновляем в базе
        success = db.update_chat_settings(chat_id, settings)
        
        if success:
            status = "✅" if settings[setting_name] else "❌"
            await callback.answer(f"Настройка изменена: {status}")
            
            # Обновляем сообщение
            await callback.message.edit_reply_markup(
                reply_markup=callback.message.reply_markup
            )
        else:
            await callback.answer("❌ Ошибка изменения настройки")
            
    except Exception as e:
        logger.error(f"Ошибка обработки настройки: {e}")
        await callback.answer("Произошла ошибка")

async def handle_filter_callback(callback: types.CallbackQuery, data: str):
    """Обработка callback для фильтров"""
    try:
        if data == "filter_add":
            await callback.message.answer(
                "🔍 **Добавление фильтра**\n\n"
                "Отправьте паттерн для фильтра (регулярное выражение):",
                parse_mode="Markdown"
            )
            # Здесь можно добавить FSM для добавления фильтра
        elif data == "filter_stats":
            chat_id = callback.message.chat.id
            stats = await filter_manager.get_filter_stats(chat_id)
            
            stats_text = (
                "📊 **Статистика фильтров**\n\n"
                f"Всего фильтров: {stats['total_filters']}\n"
                f"Активных: {stats['active_filters']}\n\n"
                "**По типам:**\n"
            )
            
            for filter_type, count in stats['by_type'].items():
                stats_text += f"• {filter_type}: {count}\n"
            
            stats_text += "\n**По действиям:**\n"
            for action, count in stats['by_action'].items():
                stats_text += f"• {action}: {count}\n"
            
            await callback.message.answer(stats_text, parse_mode="Markdown")
        else:
            filter_id = int(data.replace("filter_", ""))
            # Показываем детали фильтра
            await callback.answer(f"Фильтр {filter_id}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки фильтра: {e}")
        await callback.answer("Произошла ошибка")

async def handle_mod_action_callback(callback: types.CallbackQuery, data: str):
    """Обработка callback для действий модерации"""
    try:
        action = data.replace("mod_action_", "")
        
        if action == "warn":
            await callback.message.answer(
                "⚠️ **Предупреждение**\n\n"
                "Ответьте на сообщение пользователя командой /warn или используйте:\n"
                "/warn @username [причина]"
            )
        elif action == "mute":
            await callback.message.answer(
                "🔇 **Мут**\n\n"
                "Ответьте на сообщение пользователя командой /mute или используйте:\n"
                "/mute @username [время] [причина]"
            )
        elif action == "ban":
            await callback.message.answer(
                "🚫 **Бан**\n\n"
                "Ответьте на сообщение пользователя командой /ban или используйте:\n"
                "/ban @username [время] [причина]"
            )
        elif action == "unban":
            await callback.message.answer(
                "✅ **Разбан/Размут**\n\n"
                "Используйте команды:\n"
                "/unban @username - разбан\n"
                "/unmute @username - размут"
            )
        
        await callback.answer("Инструкция отправлена")
        
    except Exception as e:
        logger.error(f"Ошибка обработки действия модерации: {e}")
        await callback.answer("Произошла ошибка")

async def handle_mod_callback(callback: types.CallbackQuery, data: str):
    """Обработка callback для модерации"""
    try:
        if data == "mod_stats":
            chat_id = callback.message.chat.id
            stats = await get_chat_statistics(chat_id)
            
            stats_text = (
                "📊 **Статистика модерации**\n\n"
                f"**За все время:**\n"
                f"• Предупреждений: {stats['total_warnings']:,}\n"
                f"• Мутов: {stats['total_mutes']:,}\n"
                f"• Банов: {stats['total_bans']:,}\n"
                f"• Удаленных сообщений: {stats['deleted_messages']:,}\n\n"
                f"**Сегодня:**\n"
                f"• Сообщений: {stats['messages_today']:,}\n"
                f"• Новых пользователей: {stats['new_users_today']:,}"
            )
            
            await callback.message.answer(stats_text, parse_mode="Markdown")
            
        elif data == "mod_cleanup":
            await callback.message.answer(
                "🧹 **Очистка чата**\n\n"
                "Эта функция находится в разработке.\n"
                "Используйте команды модерации для удаления отдельных сообщений."
            )
        
        await callback.answer("Информация отправлена")
        
    except Exception as e:
        logger.error(f"Ошибка обработки модерации: {e}")
        await callback.answer("Произошла ошибка")

# Основная функция
async def main():
    """Основная функция бота"""
    try:
        logger.info("Запуск бота-модератора...")
        
        # Запускаем периодические задачи
        asyncio.create_task(periodic_tasks())
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")