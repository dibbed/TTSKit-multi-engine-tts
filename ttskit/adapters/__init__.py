"""Compatibility adapters package.

Provides shims that forward to `ttskit.telegram` so tests and older code
can import `ttskit.adapters.*` paths.
"""

from ..telegram.aiogram_adapter import AiogramAdapter
from ..telegram.factory import (
    AdapterType,
    check_dependencies,
    create_adapter,
    factory,
    get_available_adapters,
    get_recommended_adapter,
)
from ..telegram.pyrogram_adapter import PyrogramAdapter
from ..telegram.telebot_adapter import TelebotAdapter
from ..telegram.telethon_adapter import TelethonAdapter

__all__ = [
    "AiogramAdapter",
    "PyrogramAdapter",
    "TelebotAdapter",
    "TelethonAdapter",
    "AdapterType",
    "factory",
    "create_adapter",
    "get_available_adapters",
    "get_recommended_adapter",
    "check_dependencies",
]

# Provide submodule path expected by tests: ttskit.adapters.aiogram_adapter
import sys as _sys

from ..telegram import aiogram_adapter as _aiogram_adapter_mod

_sys.modules.setdefault(__name__ + ".aiogram_adapter", _aiogram_adapter_mod)
