"""
TTSKit: Professional Telegram TTS library and bot.

This module provides a comprehensive text-to-speech solution for Telegram bots
and applications. It includes multiple TTS engines, smart routing, caching,
and a unified bot interface for easy integration.
"""

from .bot.unified_bot import UnifiedTTSBot as TTSBot
from .cache.memory import memory_cache
from .engines import GTTSEngine, TTSEngine
from .engines.smart_router import SmartRouter
from .metrics import get_metrics_collector
from .public import (
    TTS,
    AudioOut,
    SynthConfig,
    get_engines,
    get_supported_languages,
    list_voices,
    synth,
    synth_async,
)
from .utils import parse_lang_and_text, to_opus_ogg, validate_text

__version__ = "1.0.0"

__all__ = [
    "TTSBot",
    "TTS",
    "SynthConfig",
    "AudioOut",
    "TTSEngine",
    "GTTSEngine",
    "SmartRouter",
    "to_opus_ogg",
    "parse_lang_and_text",
    "validate_text",
    "memory_cache",
    "get_metrics_collector",
    "synth",
    "synth_async",
    "list_voices",
    "get_engines",
    "get_supported_languages",
]
