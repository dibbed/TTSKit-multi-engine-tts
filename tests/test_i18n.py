"""Tests for i18n message keys and fallbacks."""

from __future__ import annotations

from ttskit.utils.i18n import t


def test_help_text_has_placeholders() -> None:
    s_fa = t("help", lang="fa", default_lang="en", max_chars=1000)
    s_en = t("help", lang="en", default_lang="en", max_chars=1000)
    assert "Default" in s_en or "پیش‌فرض" in s_fa


def test_fallback_unknown_lang() -> None:
    msg = t("empty_text", lang="xx")
    assert isinstance(msg, str)
    assert len(msg) > 0
