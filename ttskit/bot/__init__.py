"""
Telegram bot module.

This module provides the unified Telegram bot implementation
that works with multiple frameworks and TTS engines.
"""

from .unified_bot import UnifiedTTSBot as TTSBot

__all__ = ["TTSBot"]
