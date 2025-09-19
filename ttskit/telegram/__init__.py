"""Telegram adapters module for TTSKit.

This module provides adapters for various Telegram bot frameworks, allowing TTSKit
to send and receive messages, handle callbacks, and manage bot operations uniformly
across Aiogram, Pyrogram, Telebot, and Telethon.
"""

from .aiogram_adapter import AiogramAdapter
from .base import TelegramAdapter, TelegramChat, TelegramMessage, TelegramUser
from .factory import AdapterFactory, AdapterType, factory
from .pyrogram_adapter import PyrogramAdapter
from .telebot_adapter import TelebotAdapter
from .telethon_adapter import TelethonAdapter

__all__ = [
    "TelegramAdapter",
    "TelegramMessage",
    "TelegramUser",
    "TelegramChat",
    "AiogramAdapter",
    "PyrogramAdapter",
    "TelethonAdapter",
    "TelebotAdapter",
    "AdapterFactory",
    "AdapterType",
]
