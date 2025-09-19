"""
TTS engine implementations.

This module provides various text-to-speech engine implementations
including Google TTS, Edge TTS, and Piper TTS engines.
"""

from .base import TTSEngine
from .gtts_engine import GTTSEngine

__all__ = ["TTSEngine", "GTTSEngine"]

try:
    from .edge_engine import EdgeEngine

    __all__.append("EdgeEngine")
except ImportError:
    pass
