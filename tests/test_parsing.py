"""Tests for parsing utilities."""

from ttskit.utils.parsing import parse_lang_and_text, validate_text


class TestParseLangAndText:
    """Test language and text parsing."""

    def test_no_prefix(self) -> None:
        """Test parsing without language prefix."""
        lang, text = parse_lang_and_text("hello world")
        assert lang in {"ar", "en"}
        assert text == "hello world"

    def test_prefix(self) -> None:
        """Test parsing with language prefix."""
        lang, text = parse_lang_and_text("fa: سلام دنیا")
        assert lang == "fa"
        assert text == "سلام دنیا"

    def test_case_insensitive_prefix(self) -> None:
        """Test case-insensitive language prefix."""
        lang, text = parse_lang_and_text("EN: Hello")
        assert lang == "EN"
        assert text == "Hello"

    def test_empty_text(self) -> None:
        """Test empty input."""
        lang, text = parse_lang_and_text("")
        assert lang in {"ar", "en"}
        assert text == ""

    def test_only_prefix(self) -> None:
        """Test input with only prefix."""
        lang, text = parse_lang_and_text("en:")
        assert lang in {"ar", "en"}
        assert text == ""

    def test_custom_default(self) -> None:
        """Test custom default language."""
        lang, text = parse_lang_and_text("hello", "en")
        assert lang == "en"
        assert text == "hello"


class TestValidateText:
    """Test text validation."""

    def test_valid_text(self) -> None:
        """Test valid text."""
        assert validate_text("hello world") is None

    def test_empty_text(self) -> None:
        """Test empty text."""
        err = validate_text("")
        assert err is not None
        assert "خالی" in err

    def test_whitespace_only(self) -> None:
        """Test whitespace-only text."""
        err = validate_text("   ")
        assert err is not None
        assert "خالی" in err

    def test_too_long(self) -> None:
        """Test text exceeding max length."""
        long_text = "a" * 2000
        err = validate_text(long_text)
        assert err is not None
        assert "بلند" in err

    def test_custom_max_len(self) -> None:
        """Test custom max length."""
        err = validate_text("hello", max_len=3)
        assert err is not None
