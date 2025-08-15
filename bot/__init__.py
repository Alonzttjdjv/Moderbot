# Инициализация модуля ботов

from .platform import BotPlatform
from .telegram_bot import TelegramBot
from .discord_bot import DiscordBot
from .vk_bot import VKBot

__all__ = ['BotPlatform', 'TelegramBot', 'DiscordBot', 'VKBot']