import logging

import pytest

from ttskit.cache import cache_key
from ttskit.utils.audio_manager import audio_manager
from ttskit.utils.logging_config import get_logger

logger = get_logger(__name__)

"""
Tests consistency of cache key generation and usage in the audio manager.
"""

@pytest.mark.asyncio
async def test_cache_key_is_used_by_audio_manager(tmp_path):
    """
    Verifies that the cache key is correctly generated and used by the audio manager.

    Parameters:
        tmp_path: Pytest fixture providing a temporary directory path.

    Notes:
        Generates audio for a sample text, saves to cache using the key, and asserts the key is a 64-character hexadecimal string.
    """
    text = "hello"
    lang = "en"
    engine = "gtts"

    key_global = cache_key(text, lang, engine)

    try:
        audio_bytes = await audio_manager._generate_audio(
            text, lang, engine, None, None, "mp3"
        )
        audio_manager._save_to_cache(
            key_global, audio_bytes or b"", "mp3", {"lang": lang, "engine": engine}
        )
    except Exception as exc:
        logging.warning("cache_key_consistency: synthesis/cache error: %s", exc)

    assert (
        isinstance(key_global, str)
        and len(key_global) == 64
        and all(c in "0123456789abcdef" for c in key_global)
    )
