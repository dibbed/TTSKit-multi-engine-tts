"""Text processing utilities for RTL/Persian normalization in TTSKit.

Provides functions for language detection (RTL focus), text cleaning/normalization,
emoji handling, length calculation, and validation for safe TTS input.
"""

import re

from ..exceptions import TTSKitInternalError


def detect_rtl_language(text: str) -> str | None:
    """Detect if text contains RTL characters (Persian or Arabic).

    Scans for Persian or Arabic Unicode chars to identify RTL direction.

    Args:
        text: Text to check (str).

    Returns:
        str or None: 'fa' for Persian, 'ar' for Arabic, None otherwise.
    """
    if not text:
        return None

    persian_chars = set("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی")
    arabic_chars = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

    text_chars = set(text)

    if text_chars.intersection(persian_chars):
        return "fa"
    elif text_chars.intersection(arabic_chars):
        return "ar"

    return None


def clean_text_for_tts(text: str, lang: str) -> str:
    """Clean text specifically for TTS engines.

    Removes unsupported chars, normalizes spaces, strips whitespace.
    Lang param unused in current impl but reserved for future.

    Args:
        text: Raw input (str).
        lang: Language (str); not used but preserved.

    Returns:
        str: Sanitized text with basic punctuation kept.
    """
    if not text:
        return text

    text = re.sub(r'[^\w\s\.,!?;:\-\(\)\[\]{}"\']', "", text)

    text = re.sub(r"\s+", " ", text)

    text = text.strip()

    return text


def clean_text(text: str) -> str:
    """General-purpose text cleaning for non-TTS use.

    Collapses whitespace, removes zero-width chars.

    Args:
        text: Input (str).

    Returns:
        str: Cleaned text.

    Raises:
        TTSKitInternalError: On unexpected errors.
    """
    try:
        if not text:
            return ""

        text = re.sub(r"\s+", " ", text.strip())

        text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

        return text
    except Exception as e:
        raise TTSKitInternalError(f"Error cleaning text: {e}") from e


def detect_language(text: str) -> str | None:
    """Detect language (RTL focus) from text content.

    Alias for detect_rtl_language; returns None for LTR.

    Args:
        text: Text to detect (str).

    Returns:
        str or None: RTL code or None.
    """
    return detect_rtl_language(text)


def extract_emojis(text: str) -> list[str]:
    """Find and list all emojis in text using Unicode ranges.

    Matches common emoji blocks for comprehensive extraction.

    Args:
        text: Text to scan (str).

    Returns:
        list[str]: Individual emojis found.
    """
    if not text:
        return []

    emoji_pattern = re.compile(
        r"["
        r"\U0001f600-\U0001f64f"  # emoticons
        r"\U0001f300-\U0001f5ff"  # symbols & pictographs
        r"\U0001f680-\U0001f6ff"  # transport & map symbols
        r"\U0001f1e0-\U0001f1ff"  # flags
        r"\U00002600-\U000026ff"  # miscellaneous symbols
        r"\U00002700-\U000027bf"  # dingbats
        r"]+",
        flags=re.UNICODE,
    )

    return emoji_pattern.findall(text)


def remove_emojis(text: str) -> str:
    """Remove all emojis from text.

    Uses same Unicode pattern as extract_emojis to replace with empty.

    Args:
        text: Input (str).

    Returns:
        str: Text without emojis.
    """
    if not text:
        return text

    emoji_pattern = re.compile(
        r"["
        r"\U0001f600-\U0001f64f"  # emoticons
        r"\U0001f300-\U0001f5ff"  # symbols & pictographs
        r"\U0001f680-\U0001f6ff"  # transport & map symbols
        r"\U0001f1e0-\U0001f1ff"  # flags
        r"\U00002600-\U000026ff"  # miscellaneous symbols
        r"\U00002700-\U000027bf"  # dingbats
        r"]+",
        flags=re.UNICODE,
    )

    return emoji_pattern.sub("", text)


def get_text_length(text: str) -> int:
    """Count characters in text (simple len).

    Args:
        text: Text (str).

    Returns:
        int: Length; 0 if empty.
    """
    if not text:
        return 0
    return len(text)


def remove_special_characters(text: str) -> str:
    """Strip text to alphanum, spaces, and basic punctuation.

    Args:
        text: Input (str).

    Returns:
        str: Filtered text.
    """
    if not text:
        return text

    return re.sub(r"[^\w\s\.,!?;:\-\(\)\[\]{}]", "", text)


def normalize_whitespace(text: str) -> str:
    """Replace multiple whitespace with single space and strip ends.

    Args:
        text: Input (str).

    Returns:
        str: Normalized text.
    """
    if not text:
        return text

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_text(text: str) -> str:
    """Apply full normalization: whitespace + zero-width char removal.

    Combines normalize_whitespace and zero-width regex.

    Args:
        text: Input (str).

    Returns:
        str: Fully normalized text.
    """
    if not text:
        return text

    text = normalize_whitespace(text)

    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    return text


def is_persian_text(text: str) -> bool:
    """Check for Persian characters in text.

    Uses set intersection with Persian Unicode chars.

    Args:
        text: Text to check (str).

    Returns:
        bool: True if any Persian char present.
    """
    if not text:
        return False

    persian_chars = set("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی")
    text_chars = set(text)

    return bool(text_chars.intersection(persian_chars))


def is_arabic_text(text: str) -> bool:
    """Check for Arabic characters in text.

    Uses set intersection with Arabic Unicode chars.

    Args:
        text: Text (str).

    Returns:
        bool: True if any Arabic char present.
    """
    if not text:
        return False

    arabic_chars = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")
    text_chars = set(text)

    return bool(text_chars.intersection(arabic_chars))


def is_english_text(text: str) -> bool:
    """Check for English letters in text.

    Uses regex to search for a-zA-Z.

    Args:
        text: Text (str).

    Returns:
        bool: True if any English letter present.
    """
    if not text:
        return False

    english_pattern = re.compile(r"[a-zA-Z]")
    return bool(english_pattern.search(text))


def split_long_text(text: str, max_length: int = 1000) -> list[str]:
    """Split text into chunks <= max_length, preferring sentences then words.

    Handles long sentences by word split or truncation; filters empty chunks.

    Args:
        text: Long text to split (str).
        max_length: Max chars per chunk (int); default 1000.

    Returns:
        list[str]: Non-empty chunks.
    """
    if not text or len(text) <= max_length:
        return [text] if text else []

    chunks = []
    current_chunk = ""

    sentences = re.split(r"[.!?]+", text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                words = sentence.split()
                temp_chunk = ""

                for word in words:
                    if len(temp_chunk) + len(word) + 1 > max_length:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word
                        else:
                            chunks.append(word[:max_length])
                    else:
                        temp_chunk += " " + word if temp_chunk else word

                current_chunk = temp_chunk
        else:
            current_chunk += " " + sentence if current_chunk else sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [chunk for chunk in chunks if chunk]


def validate_text(text: str, max_length: int = 1000) -> str | None:
    """Validate text for TTS: check non-empty and length.

    Returns Persian error msg if invalid.

    Args:
        text: Text to validate (str).
        max_length: Max length (int); default 1000.

    Returns:
        str or None: Error if empty/too long, None if valid.
    """
    if not text or not text.strip():
        return "متن خالی است"

    if len(text) > max_length:
        return f"متن خیلی بلند است. حداکثر {max_length} کاراکتر مجاز است"

    return None
