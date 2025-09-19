"""Validation utilities for TTSKit.

This module defines supported languages/voices and provides functions to validate
language codes, voice names per engine, rate/pitch values, engine names, and user input.
Uses regex patterns and sets for efficient checks.
"""

import re
from typing import Any, Dict

# Comprehensive mapping of supported language codes to names
SUPPORTED_LANGUAGES = {
    "en": "English",
    "fa": "Persian",
    "ar": "Arabic",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "hi": "Hindi",
    "tr": "Turkish",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "ro": "Romanian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sl": "Slovenian",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ms": "Malay",
    "tl": "Filipino",
    "sw": "Swahili",
    "af": "Afrikaans",
    "sq": "Albanian",
    "am": "Amharic",
    "az": "Azerbaijani",
    "be": "Belarusian",
    "bn": "Bengali",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cy": "Welsh",
    "eu": "Basque",
    "ga": "Irish",
    "gl": "Galician",
    "gu": "Gujarati",
    "is": "Icelandic",
    "kn": "Kannada",
    "kk": "Kazakh",
    "km": "Khmer",
    "ky": "Kyrgyz",
    "lo": "Lao",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "mr": "Marathi",
    "my": "Myanmar",
    "ne": "Nepali",
    "pa": "Punjabi",
    "si": "Sinhala",
    "ta": "Tamil",
    "te": "Telugu",
    "tg": "Tajik",
    "tk": "Turkmen",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "zu": "Zulu",
}

# Dict of regex patterns and examples for validating voice names per TTS engine
VOICE_PATTERNS: Dict[str, Dict[str, Any]] = {
    "edge": {
        "pattern": r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural$",
        "examples": ["en-US-AriaNeural", "fa-IR-DilaraNeural", "ar-SA-HamedNeural"],
    },
    "gtts": {"pattern": r"^[a-z]{2}$", "examples": ["en", "fa", "ar"]},
    "piper": {"pattern": r"^[a-z_]+$", "examples": ["en_US", "fa_IR", "ar_SA"]},
}

# Acceptable ranges for speech rate (0.1-3.0) and pitch adjustment (-12.0 to 12.0 semitones)
RATE_RANGE = (0.1, 3.0)
PITCH_RANGE = (-12.0, 12.0)


def validate_language(lang: str) -> bool:
    """Check if language code is in the supported list.

    Args:
        lang: 2-letter code (str, e.g., 'en', 'fa').

    Returns:
        bool: True if supported.
    """
    return lang in SUPPORTED_LANGUAGES


def validate_voice(voice: str, engine: str) -> bool:
    """Validate voice name against engine-specific regex pattern.

    Args:
        voice: Voice identifier (str, e.g., 'en-US-AriaNeural').
        engine: Engine like 'edge', 'gtts', 'piper' (str).

    Returns:
        bool: True if matches pattern, False if invalid engine or no match.

    Notes:
        Patterns/examples in VOICE_PATTERNS global.
        Returns False if voice or engine empty.
    """
    if not voice or not engine:
        return False

    pattern_info = VOICE_PATTERNS.get(engine)
    if not pattern_info:
        return False

    pattern: str = pattern_info["pattern"]
    return bool(re.match(pattern, voice))


def validate_rate(rate: float) -> bool:
    """Check if rate is within acceptable range for speech synthesis.

    Args:
        rate: Speed multiplier (float, 0.1 to 3.0).

    Returns:
        bool: True if 0.1 <= rate <= 3.0.
    """
    return RATE_RANGE[0] <= rate <= RATE_RANGE[1]


def validate_pitch(pitch: float) -> bool:
    """Check if pitch adjustment is within range.

    Args:
        pitch: Semitones (-12.0 to 12.0).

    Returns:
        bool: True if -12.0 <= pitch <= 12.0.
    """
    return PITCH_RANGE[0] <= pitch <= PITCH_RANGE[1]


def validate_engine(engine: str) -> bool:
    """Check if engine name is supported.

    Args:
        engine: Name like 'gtts', 'edge', 'piper' (str).

    Returns:
        bool: True if in valid_engines.
    """
    valid_engines = ["gtts", "edge", "piper"]
    return engine in valid_engines


def validate_language_code(lang: str) -> bool:
    """Alias for validate_language.

    Args:
        lang: Code (str).

    Returns:
        bool: Same as validate_language.
    """
    return validate_language(lang)


def validate_voice_name(voice: str, engine: str) -> bool:
    """Alias for validate_voice.

    Args:
        voice: Name (str).
        engine: Engine (str).

    Returns:
        bool: Same as validate_voice.
    """
    return validate_voice(voice, engine)


def validate_engine_name(engine: str) -> bool:
    """Alias for validate_engine.

    Args:
        engine: Name (str).

    Returns:
        bool: Same as validate_engine.
    """
    return validate_engine(engine)


def validate_user_input(text: str, lang: str, engine: str | None = None) -> bool:
    """Validate combined user input for TTS: text non-empty, lang/engine if provided.

    Args:
        text: Input text (str).
        lang: Language code (str).
        engine: Optional engine (str or None).

    Returns:
        bool: True if text non-empty and lang valid (engine if given).
    """
    if not text or not text.strip():
        return False

    if not validate_language(lang):
        return False

    if engine and not validate_engine(engine):
        return False

    return True


def sanitize_text(text: str) -> str:
    """Basic sanitization: remove <>"'& and normalize whitespace.

    Args:
        text: Raw text (str).

    Returns:
        str: Safe, stripped text.
    """
    if not text:
        return ""

    text = re.sub(r"[<>\"'&]", "", text)

    text = re.sub(r"\s+", " ", text.strip())

    return text
