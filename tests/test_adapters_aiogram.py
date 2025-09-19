"""Tests for Aiogram adapter."""

from unittest.mock import Mock, patch

import pytest

from ttskit.telegram.aiogram_adapter import AiogramAdapter
from ttskit.telegram.base import TelegramChat, TelegramMessage, TelegramUser


class TestAiogramAdapter:
    """Test cases for AiogramAdapter."""

    def test_initialization(self):
        """Test adapter initialization."""
        adapter = AiogramAdapter("test_token")
        assert adapter.bot_token == "test_token"
        assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop methods."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            with patch("ttskit.telegram.aiogram_adapter.Dispatcher") as mock_dp:
                mock_bot_instance = Mock()
                mock_dp_instance = Mock()
                mock_bot.return_value = mock_bot_instance
                mock_dp.return_value = mock_dp_instance

                await adapter.start()
                assert adapter.is_running

                await adapter.stop()
                assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending text message."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "test_user"
            mock_message.from_user.first_name = "Test"
            mock_message.text = "Hello"
            mock_message.date = 1234567890

            mock_bot_instance.send_message.return_value = mock_message

            result = await adapter.send_message(456, "Hello")

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456

    @pytest.mark.asyncio
    async def test_send_voice(self):
        """Test sending voice message."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "test_user"
            mock_message.from_user.first_name = "Test"
            mock_message.text = None
            mock_message.date = 1234567890

            mock_bot_instance.send_voice.return_value = mock_message

            result = await adapter.send_voice(456, b"fake audio", "Test voice")

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456

    @pytest.mark.asyncio
    async def test_send_audio(self):
        """Test sending audio file."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "test_user"
            mock_message.from_user.first_name = "Test"
            mock_message.text = None
            mock_message.date = 1234567890

            mock_bot_instance.send_audio.return_value = mock_message

            result = await adapter.send_audio(456, b"fake audio", "Test audio")

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456

    @pytest.mark.asyncio
    async def test_edit_message_text(self):
        """Test editing message text."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "test_user"
            mock_message.from_user.first_name = "Test"
            mock_message.text = "Edited text"
            mock_message.date = 1234567890

            mock_bot_instance.edit_message_text.return_value = mock_message

            result = await adapter.edit_message_text(456, 123, "Edited text")

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.text == "Edited text"

    @pytest.mark.asyncio
    async def test_delete_message(self):
        """Test deleting message."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_bot_instance.delete_message.return_value = True

            result = await adapter.delete_message(456, 123)

            assert result is True

    @pytest.mark.asyncio
    async def test_get_chat(self):
        """Test getting chat information."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_chat = Mock()
            mock_chat.id = 456
            mock_chat.type = "private"
            mock_chat.title = "Test Chat"
            mock_chat.username = "test_chat"

            mock_bot_instance.get_chat.return_value = mock_chat

            result = await adapter.get_chat(456)

            assert isinstance(result, TelegramChat)
            assert result.id == 456
            assert result.type == "private"

    @pytest.mark.asyncio
    async def test_get_user(self):
        """Test getting user information."""
        adapter = AiogramAdapter("test_token")

        with patch("ttskit.telegram.aiogram_adapter.Bot") as mock_bot:
            mock_bot_instance = Mock()
            mock_bot.return_value = mock_bot_instance

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "test_user"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.language_code = "en"
            mock_user.is_bot = False
            mock_user.is_premium = False

            mock_bot_instance.get_chat_member.return_value.user = mock_user

            result = await adapter.get_user(789)

            assert isinstance(result, TelegramUser)
            assert result.id == 789
            assert result.username == "test_user"

    def test_set_handlers(self):
        """Test setting handlers."""
        adapter = AiogramAdapter("test_token")

        def mock_handler(message):
            pass

        def mock_callback_handler(message):
            pass

        def mock_error_handler(error, context):
            pass

        adapter.set_message_handler(mock_handler)
        adapter.set_callback_handler(mock_callback_handler)
        adapter.set_error_handler(mock_error_handler)

        assert adapter._message_handler == mock_handler
        assert adapter._callback_handler == mock_callback_handler
        assert adapter._error_handler == mock_error_handler

    def test_parse_command(self):
        """Test command parsing."""
        adapter = AiogramAdapter("test_token")

        result = adapter.parse_command("/voice Hello world")

        assert isinstance(result, dict)
        assert "text" in result
        assert "lang" in result
        assert "engine" in result
        assert "voice" in result
        assert "rate" in result
        assert "pitch" in result

        assert result["text"] == "Hello world"
        assert result["lang"] == "en"

    def test_parse_command_with_language(self):
        """Test command parsing with language prefix."""
        adapter = AiogramAdapter("test_token")

        result = adapter.parse_command("[fa]: سلام دنیا")

        assert result["text"] == "سلام دنیا"
        assert result["lang"] == "fa"

    def test_parse_command_with_engine(self):
        """Test command parsing with engine prefix."""
        adapter = AiogramAdapter("test_token")

        result = adapter.parse_command("{edge} Hello world")

        assert result["text"] == "Hello world"
        assert result["engine"] == "edge"

    def test_parse_command_with_voice(self):
        """Test command parsing with voice prefix."""
        adapter = AiogramAdapter("test_token")

        result = adapter.parse_command("(voice:en-US-AriaNeural) Hello world")

        assert result["text"] == "Hello world"
        assert result["voice"] == "en-US-AriaNeural"

    def test_parse_command_with_rate(self):
        """Test command parsing with rate prefix."""
        adapter = AiogramAdapter("test_token")

        result = adapter.parse_command("+10% Hello world")

        assert result["text"] == "Hello world"
        assert result["rate"] == 1.1

    def test_parse_command_with_pitch(self):
        """Test command parsing with pitch prefix."""
        adapter = AiogramAdapter("test_token")

        result = adapter.parse_command("@+2st Hello world")

        assert result["text"] == "Hello world"
        assert result["pitch"] == 2.0
