"""Tests for text utilities."""

import pytest

from ttskit.utils.text import (
    clean_text,
    detect_language,
    extract_emojis,
    get_text_length,
    is_arabic_text,
    is_english_text,
    is_persian_text,
    normalize_text,
    remove_emojis,
    split_long_text,
)
from ttskit.utils.text import validate_text as validate_text_utils


class TestTextValidation:
    """Test text validation functions."""

    def test_validate_text_utils_valid(self):
        """Test validate_text_utils with valid text."""
        result = validate_text_utils("Hello world")
        assert result is None

    def test_validate_text_utils_empty(self):
        """Test validate_text_utils with empty text."""
        result = validate_text_utils("")
        assert result == "متن خالی است"

    def test_validate_text_utils_whitespace_only(self):
        """Test validate_text_utils with whitespace only."""
        result = validate_text_utils("   \n\t  ")
        assert result == "متن خالی است"

    def test_validate_text_utils_too_long(self):
        """Test validate_text_utils with text too long."""
        long_text = "a" * 10001
        result = validate_text_utils(long_text)
        assert "خیلی بلند" in result

    def test_validate_text_utils_custom_max_length(self):
        """Test validate_text_utils with custom max length."""
        text = "a" * 100
        result = validate_text_utils(text, max_length=50)
        assert "خیلی بلند" in result

    def test_validate_text_utils_custom_max_length_valid(self):
        """Test validate_text_utils with custom max length valid."""
        text = "a" * 25
        result = validate_text_utils(text, max_length=50)
        assert result is None


class TestTextCleaning:
    """Test text cleaning functions."""

    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        text = "  Hello   world  \n\t  "
        result = clean_text(text)
        assert result == "Hello world"

    def test_clean_text_empty(self):
        """Test cleaning empty text."""
        result = clean_text("")
        assert result == ""

    def test_clean_text_whitespace_only(self):
        """Test cleaning whitespace only text."""
        result = clean_text("   \n\t  ")
        assert result == ""

    def test_clean_text_with_unicode(self):
        """Test cleaning text with unicode characters."""
        text = "  Hello\u00a0world  "
        result = clean_text(text)
        assert result == "Hello world"

    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        text = "  Hello World!  "
        result = normalize_text(text)
        assert result == "Hello World!"

    def test_normalize_text_persian(self):
        """Test Persian text normalization."""
        text = "  سلام دنیا  "
        result = normalize_text(text)
        assert result == "سلام دنیا"

    def test_normalize_text_arabic(self):
        """Test Arabic text normalization."""
        text = "  مرحبا بالعالم  "
        result = normalize_text(text)
        assert result == "مرحبا بالعالم"


class TestLanguageDetection:
    """Test language detection functions."""

    def test_is_english_text(self):
        """Test English text detection."""
        assert is_english_text("Hello world") is True
        assert is_english_text("This is English text") is True
        assert is_english_text("سلام دنیا") is False
        assert is_english_text("مرحبا بالعالم") is False

    def test_is_persian_text(self):
        """Test Persian text detection."""
        assert is_persian_text("سلام دنیا") is True
        assert is_persian_text("این متن فارسی است") is True
        assert is_persian_text("Hello world") is False
        assert (
            is_persian_text("مرحبا بالعالم") is True
        )

    def test_is_arabic_text(self):
        """Test Arabic text detection."""
        assert is_arabic_text("مرحبا بالعالم") is True
        assert is_arabic_text("هذا نص عربي") is True
        assert is_arabic_text("Hello world") is False
        assert (
            is_arabic_text("سلام دنیا") is True
        )

    def test_detect_language_english(self):
        """Test language detection for English."""
        result = detect_language("Hello world")
        assert result is None

    def test_detect_language_persian(self):
        """Test language detection for Persian."""
        result = detect_language("سلام دنیا")
        assert result == "fa"

    def test_detect_language_arabic(self):
        """Test language detection for Arabic."""
        result = detect_language("مرحبا بالعالم")
        assert result == "fa"

    def test_detect_language_mixed(self):
        """Test language detection for mixed text."""
        result = detect_language("Hello سلام")
        assert result == "fa"

    def test_detect_language_empty(self):
        """Test language detection for empty text."""
        result = detect_language("")
        assert result is None

    def test_detect_language_unknown(self):
        """Test language detection for unknown text."""
        result = detect_language("123456789")
        assert result is None


class TestEmojiHandling:
    """Test emoji handling functions."""

    def test_extract_emojis(self):
        """Test emoji extraction."""
        text = "Hello 😀 world 🌍"
        result = extract_emojis(text)
        assert "😀" in result
        assert "🌍" in result

    def test_extract_emojis_no_emojis(self):
        """Test emoji extraction with no emojis."""
        text = "Hello world"
        result = extract_emojis(text)
        assert result == []

    def test_remove_emojis(self):
        """Test emoji removal."""
        text = "Hello 😀 world 🌍"
        result = remove_emojis(text)
        assert result == "Hello  world "

    def test_remove_emojis_no_emojis(self):
        """Test emoji removal with no emojis."""
        text = "Hello world"
        result = remove_emojis(text)
        assert result == "Hello world"

    def test_remove_emojis_empty(self):
        """Test emoji removal with empty text."""
        result = remove_emojis("")
        assert result == ""


class TestTextLength:
    """Test text length functions."""

    def test_get_text_length_basic(self):
        """Test basic text length calculation."""
        text = "Hello world"
        result = get_text_length(text)
        assert result == 11

    def test_get_text_length_unicode(self):
        """Test text length with unicode characters."""
        text = "سلام دنیا"
        result = get_text_length(text)
        assert result == 9

    def test_get_text_length_empty(self):
        """Test text length with empty text."""
        result = get_text_length("")
        assert result == 0

    def test_get_text_length_whitespace(self):
        """Test text length with whitespace."""
        text = "  Hello  "
        result = get_text_length(text)
        assert result == 9


class TestTextSplitting:
    """Test text splitting functions."""

    def test_split_long_text_short(self):
        """Test splitting short text."""
        text = "Short text"
        result = split_long_text(text, max_length=100)
        assert result == ["Short text"]

    def test_split_long_text_long(self):
        """Test splitting long text."""
        text = "This is a very long text that should be split into multiple parts"
        result = split_long_text(text, max_length=20)
        assert len(result) > 1
        assert all(len(part) <= 20 for part in result)

    def test_split_long_text_empty(self):
        """Test splitting empty text."""
        result = split_long_text("", max_length=10)
        assert result == []

    def test_split_long_text_exact_length(self):
        """Test splitting text of exact max length."""
        text = "a" * 20
        result = split_long_text(text, max_length=20)
        assert result == [text]

    def test_split_long_text_with_sentences(self):
        """Test splitting text with sentences."""
        text = "First sentence. Second sentence. Third sentence."
        result = split_long_text(text, max_length=30)
        assert len(result) > 1
        assert all(len(part) <= 30 for part in result)


class TestTextUtilsIntegration:
    """Integration tests for text utilities."""

    def test_complete_text_processing(self):
        """Test complete text processing pipeline."""
        text = "  Hello 😀 world! This is a test.  "

        cleaned = clean_text(text)
        assert cleaned == "Hello 😀 world! This is a test."

        language = detect_language(cleaned)
        assert language is None

        no_emojis = remove_emojis(cleaned)
        assert no_emojis == "Hello  world! This is a test."

        length = get_text_length(no_emojis)
        assert length > 0

        validation_result = validate_text_utils(no_emojis)
        assert validation_result is None

    def test_multilingual_text_processing(self):
        """Test processing multilingual text."""
        texts = ["Hello world", "سلام دنیا", "مرحبا بالعالم", "Hello سلام مرحبا"]

        for text in texts:
            cleaned = clean_text(text)
            language = detect_language(cleaned)
            length = get_text_length(cleaned)
            is_valid = validate_text_utils(cleaned)

            assert isinstance(cleaned, str)
            assert language in [None, "fa", "ar"]
            assert length >= 0
            assert isinstance(is_valid, str | type(None))

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        edge_cases = [
            "",
            "   ",
            "a" * 10000,
            "🚀" * 100,
            "Hello\n\n\nWorld",
            "Tab\t\t\tText",
            "Mixed 123 numbers",
            "Special chars: !@#$%^&*()",
        ]

        for text in edge_cases:
            try:
                cleaned = clean_text(text)
                language = detect_language(cleaned)
                length = get_text_length(cleaned)
                validation_result = validate_text_utils(cleaned)

                assert isinstance(cleaned, str)
                assert language in [None, "fa", "ar"]
                assert length >= 0
                assert isinstance(validation_result, str | type(None))
            except Exception as e:
                pytest.fail(f"Edge case '{text}' raised exception: {e}")
