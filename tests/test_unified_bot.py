"""Tests for Unified TTS Bot."""

from unittest.mock import Mock, patch

import pytest

from ttskit.bot.unified_bot import UnifiedTTSBot
from ttskit.telegram.base import MessageType, TelegramMessage, TelegramUser


class TestUnifiedTTSBot:
    """Test UnifiedTTSBot class."""

    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return UnifiedTTSBot(
            bot_token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
            adapter_type="aiogram",
            cache_enabled=False,
            audio_processing=False,
        )

    @pytest.fixture
    def mock_message(self):
        """Create mock message for testing."""
        user = TelegramUser(
            id=12345, username="testuser", first_name="Test", last_name="User"
        )

        return TelegramMessage(
            id=1,
            chat_id=12345,
            user=user,
            text="/tts Hello World",
            message_type=MessageType.TEXT,
        )

    @pytest.mark.asyncio
    async def test_initialize(self, bot):
        """Test bot initialization."""
        with patch(
            "ttskit.telegram.factory.factory.create_adapter"
        ) as mock_adapter_factory:
            with patch("ttskit.engines.factory.setup_registry") as mock_setup_registry:
                with patch("ttskit.engines.smart_router.SmartRouter") as mock_router:
                    mock_adapter = Mock()
                    mock_adapter_factory.return_value = mock_adapter

                    mock_router_instance = Mock()
                    mock_router.return_value = mock_router_instance

                    await bot.initialize()

                    assert bot.adapter is not None
                    assert bot.smart_router is not None
                    mock_adapter_factory.assert_called_once()
                    mock_setup_registry.assert_called_once()

    def test_is_tts_request(self, bot):
        """Test TTS request detection."""
        assert bot._is_tts_request("/tts Hello World")
        assert bot._is_tts_request("/speak Hello World")
        assert bot._is_tts_request("/voice Hello World")
        assert bot._is_tts_request("/صدا سلام دنیا")
        assert bot._is_tts_request("/تکلم سلام دنیا")

        assert bot._is_tts_request("Hello World")
        assert bot._is_tts_request("سلام دنیا")

        assert not bot._is_tts_request("/help")
        assert not bot._is_tts_request("/start")
        assert not bot._is_tts_request("")

    def test_extract_tts_params(self, bot):
        """Test TTS parameter extraction."""
        text, lang = bot._extract_tts_params("/tts Hello World")
        assert text == "Hello World"
        assert lang == "fa"

        text, lang = bot._extract_tts_params("/tts [en] Hello World")
        assert text == "Hello World"
        assert lang == "en"

        text, lang = bot._extract_tts_params("Hello World")
        assert text == "Hello World"
        assert lang == "fa"

        text, lang = bot._extract_tts_params("سلام دنیا")
        assert text == "سلام دنیا"
        assert lang == "fa"

    @pytest.mark.asyncio
    async def test_handle_message(self, bot, mock_message):
        """Test message handling."""
        with patch.object(bot, "_process_tts_request") as mock_process:
            await bot._handle_message(mock_message)
            mock_process.assert_called_once_with(mock_message, "Hello World", "fa")

    @pytest.mark.asyncio
    async def test_handle_message_non_text(self, bot):
        """Test handling non-text messages."""
        user = TelegramUser(id=12345, username="testuser")
        voice_message = TelegramMessage(
            id=1, chat_id=12345, user=user, text=None, message_type=MessageType.VOICE
        )

        with patch.object(bot, "_process_tts_request") as mock_process:
            await bot._handle_message(voice_message)
            mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_non_tts(self, bot):
        """Test handling non-TTS messages."""
        user = TelegramUser(id=12345, username="testuser")
        help_message = TelegramMessage(
            id=1, chat_id=12345, user=user, text="/help", message_type=MessageType.TEXT
        )

        with patch.object(bot, "_process_tts_request") as mock_process:
            await bot._handle_message(help_message)
            mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_tts_request(self, bot, mock_message):
        """Test TTS request processing."""
        with patch.object(bot, "smart_router") as mock_router:
            with patch.object(bot, "adapter") as mock_adapter:
                mock_router.synth_async.return_value = (b"audio_data", "gtts")

                mock_adapter.send_message.return_value = Mock(id=2)
                mock_adapter.send_voice.return_value = Mock()
                mock_adapter.delete_message.return_value = True

                await bot._process_tts_request(mock_message, "Hello World", "en")

                mock_adapter.send_message.assert_called_once()
                mock_adapter.send_voice.assert_called_once()
                mock_adapter.delete_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_tts_request_cache_hit(self, bot, mock_message):
        """Test TTS request processing with cache hit."""
        with patch.object(bot, "smart_router") as mock_router:
            with patch.object(bot, "adapter") as mock_adapter:
                with patch(
                    "ttskit.utils.audio_manager.audio_manager"
                ) as mock_audio_manager:
                    mock_audio_manager.get_audio.return_value = b"cached_audio_data"

                    mock_adapter.send_message.return_value = Mock(id=2)
                    mock_adapter.send_voice.return_value = Mock()
                    mock_adapter.delete_message.return_value = True

                    await bot._process_tts_request(mock_message, "Hello World", "en")

                    mock_audio_manager.get_audio.assert_called_once()
                    mock_router.synth_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_tts_request_engine_failure(self, bot, mock_message):
        """Test TTS request processing with engine failure."""
        with patch.object(bot, "smart_router") as mock_router:
            with patch.object(bot, "adapter") as mock_adapter:
                from ttskit.exceptions import AllEnginesFailedError

                async def mock_synth_async(*args, **kwargs):
                    raise AllEnginesFailedError("All engines failed")

                mock_router.synth_async = mock_synth_async

                mock_adapter.send_message.return_value = Mock(id=2)

                bot.cache_enabled = False

                bot.awaitable = lambda func: func

                await bot._process_tts_request(mock_message, "Hello World", "en")

                mock_adapter.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_send_error_message(self, bot):
        """Test error message sending."""
        with patch.object(bot, "adapter") as mock_adapter:
            await bot._send_error_message(12345, "Test error")
            mock_adapter.send_message.assert_called_once_with(12345, "❌ Test error")

    def test_get_stats(self, bot):
        """Test statistics retrieval."""
        bot.stats["messages_processed"] = 10
        bot.stats["synthesis_requests"] = 5
        bot.stats["cache_hits"] = 3
        bot.stats["cache_misses"] = 2
        bot.stats["total_processing_time"] = 10.0

        stats = bot.get_stats()

        assert stats["messages_processed"] == 10
        assert stats["synthesis_requests"] == 5
        assert stats["cache_hits"] == 3
        assert stats["cache_misses"] == 2
        assert stats["avg_processing_time"] == 2.0
        assert stats["cache_hit_rate"] == 0.6

    def test_reset_stats(self, bot):
        """Test statistics reset."""
        bot.stats["messages_processed"] = 10
        bot.stats["synthesis_requests"] = 5

        bot.reset_stats()

        assert bot.stats["messages_processed"] == 0
        assert bot.stats["synthesis_requests"] == 0
        assert bot.stats["cache_hits"] == 0
        assert bot.stats["cache_misses"] == 0

    @pytest.mark.asyncio
    async def test_get_engine_info(self, bot):
        """Test engine information retrieval."""
        with patch.object(bot, "smart_router") as mock_router:
            with patch("ttskit.engines.registry.registry") as mock_registry:
                mock_registry.get_available_engines.return_value = ["gtts", "edge"]
                mock_registry.get_capabilities_summary.return_value = {
                    "gtts": {"offline": False, "languages": ["en"]},
                    "edge": {"offline": False, "languages": ["en", "fa"]},
                }

                mock_router.get_all_stats.return_value = {
                    "gtts": {"total_requests": 10, "success_rate": 0.9},
                    "edge": {"total_requests": 5, "success_rate": 0.8},
                }
                mock_router.get_engine_ranking.return_value = [
                    ("gtts", 0.9),
                    ("edge", 0.8),
                ]

                engine_info = await bot.get_engine_info()

                assert "available_engines" in engine_info
                assert "engine_capabilities" in engine_info
                assert "engine_stats" in engine_info
                assert "engine_rankings" in engine_info

    def test_setup_engine_preferences(self, bot):
        """Test engine preferences setup."""
        bot.engine_preferences = {"fa": ["edge", "piper"], "en": ["gtts", "edge"]}

        with patch("ttskit.engines.registry.registry") as mock_registry:
            bot._setup_engine_preferences()

            mock_registry.set_policy.assert_any_call("fa", ["edge", "piper"])
            mock_registry.set_policy.assert_any_call("en", ["gtts", "edge"])

    @pytest.mark.asyncio
    async def test_start_stop(self, bot):
        """Test bot start and stop."""
        with patch.object(bot, "initialize") as mock_init:
            with patch.object(bot, "adapter") as mock_adapter:
                await bot.start()
                mock_init.assert_called_once()
                mock_adapter.start.assert_called_once()
                assert bot.is_running

                await bot.stop()
                mock_adapter.stop.assert_called_once()
                assert not bot.is_running

    def test_property_is_running(self, bot):
        """Test is_running property."""
        assert not bot.is_running
        bot._running = True
        assert bot.is_running
