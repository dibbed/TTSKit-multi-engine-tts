"""Text parsing and validation utilities for TTSKit.

This module provides functions to parse optional language prefixes from user input
(e.g., "fa: text") and validate text length against configurable limits.
"""

import re

from ..config import settings

# Regex pattern for detecting language prefixes like "fa: hello"
_LANG_PREFIX = re.compile(r"^(?P<lang>[a-zA-Z_-]{2,5})\s*:\s*(?P<rest>.*)$", re.DOTALL)


def parse_lang_and_text(text: str, default_lang: str = None) -> tuple[str, str]:
    """Parse optional language prefix from input text and extract clean text.

    Uses regex to match prefixes like "fa: hello", returning lang and rest.
    Falls back to default_lang if no prefix or empty after prefix.

    Args:
        text: User input string, possibly prefixed (e.g., "en: Hello").
        default_lang: Fallback language code (str or None); uses settings.default_lang if None.

    Returns:
        tuple[str, str]: (detected_or_default_lang, stripped_text_without_prefix).

    Notes:
        Strips whitespace from input and extracted parts.
        Matches lang as 2-5 chars [a-zA-Z_-], followed by ": " and rest (DOTALL for multiline).
        If rest is empty after match, returns default_lang and empty string.
    """
    default_lang = default_lang or settings.default_lang
    text = (text or "").strip()

    if not text:
        return default_lang, ""

    m = _LANG_PREFIX.match(text)
    if m:
        lang = m.group("lang").strip()
        rest = (m.group("rest") or "").strip()
        if rest == "":
            return default_lang, ""
        return lang, rest

    return default_lang, text


def validate_text(text: str, max_len: int = None) -> str | None:
    """Validate text for emptiness and length limits.

    Strips input and checks against max_len; returns error message in Persian if invalid.

    Args:
        text: Input text to check (str).
        max_len: Maximum allowed length (int or None); defaults to settings.max_chars.

    Returns:
        str or None: Error message if invalid (empty or too long), None if valid.
    """
    max_len = max_len or settings.max_chars
    text = (text or "").strip()

    if not text:
        return "متن خالی است 🙂 لطفاً متنی وارد کنید."

    if len(text) > max_len:
        return f"متن خیلی بلند است؛ حداکثر {max_len} کاراکتر مجاز است."

    return None
