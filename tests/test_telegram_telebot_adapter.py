"""Comprehensive tests for Telebot adapter."""

from unittest.mock import Mock, patch

import pytest

from ttskit.telegram.base import (
    MessageType,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)
from ttskit.telegram.telebot_adapter import TelebotAdapter


class TestTelebotAdapter:
    """Test cases for TelebotAdapter class."""

    def test_telebot_adapter_initialization(self):
        """Test TelebotAdapter initialization."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            assert adapter.bot_token == "test_token"
            assert not adapter.is_running
            assert adapter._message_handler is None
            assert adapter._callback_handler is None
            assert adapter._error_handler is None
            assert adapter._loop is None

    @pytest.mark.asyncio
    async def test_telebot_adapter_start(self):
        """Test TelebotAdapter start method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            with patch("threading.Thread") as mock_thread:
                mock_thread_instance = Mock()
                mock_thread.return_value = mock_thread_instance

                await adapter.start()

                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()
                assert adapter.is_running

    @pytest.mark.asyncio
    async def test_telebot_adapter_start_exception(self):
        """Test TelebotAdapter start method with exception."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            with patch("threading.Thread", side_effect=Exception("Thread failed")):
                with pytest.raises(Exception, match="Thread failed"):
                    await adapter.start()

                assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_telebot_adapter_stop(self):
        """Test TelebotAdapter stop method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")
            adapter._running = True

            await adapter.stop()

            mock_bot.stop_polling.assert_called_once()
            assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_telebot_adapter_stop_exception(self):
        """Test TelebotAdapter stop method with exception."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_bot.stop_polling.side_effect = Exception("Stop failed")
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")
            adapter._running = True

            await adapter.stop()

            assert not adapter.is_running

    def test_telebot_adapter_setup_handlers(self):
        """Test TelebotAdapter _setup_handlers method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            def mock_message_handler(message):
                pass

            def mock_callback_handler(callback):
                pass

            def mock_error_handler(error, context):
                pass

            adapter.set_message_handler(mock_message_handler)
            adapter.set_callback_handler(mock_callback_handler)
            adapter.set_error_handler(mock_error_handler)

            adapter._setup_handlers()

            assert mock_bot.message_handler.called
            assert mock_bot.callback_query_handler.called

    def test_telebot_adapter_parse_callback(self):
        """Test TelebotAdapter _parse_callback method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_callback = Mock()
            mock_callback.from_user.id = 789
            mock_callback.from_user.username = "testuser"
            mock_callback.from_user.first_name = "Test"
            mock_callback.from_user.last_name = "User"
            mock_callback.from_user.language_code = "en"
            mock_callback.from_user.is_bot = False
            mock_callback.from_user.is_premium = False
            mock_callback.message.message_id = 123
            mock_callback.message.chat.id = 456
            mock_callback.data = "callback_data"

            result = adapter._parse_callback(mock_callback)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456
            assert result.text == "callback_data"
            assert result.message_type == MessageType.TEXT

    def test_telebot_adapter_parse_callback_no_message(self):
        """Test TelebotAdapter _parse_callback method with no message."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_callback = Mock()
            mock_callback.from_user.id = 789
            mock_callback.from_user.username = "testuser"
            mock_callback.from_user.first_name = "Test"
            mock_callback.from_user.last_name = "User"
            mock_callback.from_user.language_code = "en"
            mock_callback.from_user.is_bot = False
            mock_callback.from_user.is_premium = False
            mock_callback.message = None
            mock_callback.data = "callback_data"

            result = adapter._parse_callback(mock_callback)

            assert isinstance(result, TelegramMessage)
            assert result.id == 0
            assert result.chat_id == 0
            assert result.text == "callback_data"

    @pytest.mark.asyncio
    async def test_telebot_adapter_send_message(self):
        """Test TelebotAdapter send_message method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = "Hello"
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = None
            mock_message.entities = None

            mock_bot.send_message.return_value = mock_message

            result = await adapter.send_message(456, "Hello")

            mock_bot.send_message.assert_called_once_with(
                chat_id=456, text="Hello", reply_to_message_id=None, parse_mode=None
            )

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456
            assert result.text == "Hello"

    @pytest.mark.asyncio
    async def test_telebot_adapter_send_message_exception(self):
        """Test TelebotAdapter send_message method with exception."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_bot.send_message.side_effect = Exception("Send failed")
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            with pytest.raises(Exception, match="Send failed"):
                await adapter.send_message(456, "Hello")

    @pytest.mark.asyncio
    async def test_telebot_adapter_send_voice(self):
        """Test TelebotAdapter send_voice method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = None
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = "Voice message"
            mock_message.entities = None

            mock_bot.send_voice.return_value = mock_message

            result = await adapter.send_voice(456, b"fake_voice_data", "Voice message")

            mock_bot.send_voice.assert_called_once()
            assert isinstance(result, TelegramMessage)
            assert result.id == 123

    @pytest.mark.asyncio
    async def test_telebot_adapter_send_audio(self):
        """Test TelebotAdapter send_audio method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = None
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = "Audio file"
            mock_message.entities = None

            mock_bot.send_audio.return_value = mock_message

            result = await adapter.send_audio(456, b"fake_audio_data", "Audio file")

            mock_bot.send_audio.assert_called_once()
            assert isinstance(result, TelegramMessage)
            assert result.id == 123

    @pytest.mark.asyncio
    async def test_telebot_adapter_send_document(self):
        """Test TelebotAdapter send_document method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = None
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = "Document"
            mock_message.entities = None

            mock_bot.send_document.return_value = mock_message

            result = await adapter.send_document(
                456, b"fake_doc_data", "test.pdf", "Document"
            )

            mock_bot.send_document.assert_called_once()
            assert isinstance(result, TelegramMessage)
            assert result.id == 123

    @pytest.mark.asyncio
    async def test_telebot_adapter_edit_message_text(self):
        """Test TelebotAdapter edit_message_text method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = "Edited text"
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = None
            mock_message.entities = None

            mock_bot.edit_message_text.return_value = mock_message

            result = await adapter.edit_message_text(456, 123, "Edited text")

            mock_bot.edit_message_text.assert_called_once_with(
                chat_id=456, message_id=123, text="Edited text", parse_mode=None
            )

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.text == "Edited text"

    @pytest.mark.asyncio
    async def test_telebot_adapter_delete_message(self):
        """Test TelebotAdapter delete_message method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_bot.delete_message.return_value = True

            result = await adapter.delete_message(456, 123)

            mock_bot.delete_message.assert_called_once_with(chat_id=456, message_id=123)
            assert result is True

    @pytest.mark.asyncio
    async def test_telebot_adapter_delete_message_exception(self):
        """Test TelebotAdapter delete_message method with exception."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_bot.delete_message.side_effect = Exception("Delete failed")
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            result = await adapter.delete_message(456, 123)

            assert result is False

    @pytest.mark.asyncio
    async def test_telebot_adapter_get_chat(self):
        """Test TelebotAdapter get_chat method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_chat = Mock()
            mock_chat.id = 456
            mock_chat.type = "private"
            mock_chat.title = "Test Chat"
            mock_chat.username = "testchat"
            mock_chat.first_name = "Test"
            mock_chat.last_name = "Chat"
            mock_chat.description = "Test description"
            mock_chat.invite_link = "https://t.me/testchat"

            mock_bot.get_chat.return_value = mock_chat

            result = await adapter.get_chat(456)

            mock_bot.get_chat.assert_called_once_with(456)

            assert isinstance(result, TelegramChat)
            assert result.id == 456
            assert result.type == "private"
            assert result.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_telebot_adapter_get_user(self):
        """Test TelebotAdapter get_user method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.language_code = "en"
            mock_user.is_bot = False
            mock_user.is_premium = True

            mock_bot.get_chat.return_value = mock_user

            result = await adapter.get_user(789)

            mock_bot.get_chat.assert_called_once_with(789)

            assert isinstance(result, TelegramUser)
            assert result.id == 789
            assert result.username == "testuser"
            assert result.is_premium is True

    def test_telebot_adapter_set_handlers(self):
        """Test TelebotAdapter handler setting."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            def mock_message_handler(message):
                pass

            def mock_callback_handler(callback):
                pass

            def mock_error_handler(error, context):
                pass

            adapter.set_message_handler(mock_message_handler)
            adapter.set_callback_handler(mock_callback_handler)
            adapter.set_error_handler(mock_error_handler)

            assert adapter._message_handler == mock_message_handler
            assert adapter._callback_handler == mock_callback_handler
            assert adapter._error_handler == mock_error_handler

    def test_telebot_adapter_parse_message_text(self):
        """Test TelebotAdapter _parse_message method for text message."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = "Hello world"
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = None
            mock_message.entities = None
            mock_message.voice = None
            mock_message.audio = None
            mock_message.document = None
            mock_message.photo = None
            mock_message.video = None
            mock_message.sticker = None
            mock_message.location = None
            mock_message.contact = None
            mock_message.poll = None

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456
            assert result.text == "Hello world"
            assert result.message_type == MessageType.TEXT

    def test_telebot_adapter_parse_message_voice(self):
        """Test TelebotAdapter _parse_message method for voice message."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = None
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = "Voice message"
            mock_message.entities = None

            mock_message.voice = Mock()

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.message_type == MessageType.VOICE
            assert result.caption == "Voice message"

    def test_telebot_adapter_parse_message_with_reply(self):
        """Test TelebotAdapter _parse_message method with reply."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_reply_message = Mock()
            mock_reply_message.message_id = 10

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = "Reply message"
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = None
            mock_message.entities = None
            mock_message.reply_to_message = mock_reply_message

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.reply_to_message_id == 10

    def test_telebot_adapter_parse_message_with_entities(self):
        """Test TelebotAdapter _parse_message method with entities."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_entity1 = Mock()
            mock_entity1.__dict__ = {"type": "bold", "offset": 0, "length": 5}
            mock_entity2 = Mock()
            mock_entity2.__dict__ = {"type": "italic", "offset": 6, "length": 5}

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = "Hello world"
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = None
            mock_message.entities = [mock_entity1, mock_entity2]

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.entities == [
                {"type": "bold", "offset": 0, "length": 5},
                {"type": "italic", "offset": 6, "length": 5},
            ]

    def test_telebot_adapter_parse_user(self):
        """Test TelebotAdapter _parse_user method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.language_code = "en"
            mock_user.is_bot = False
            mock_user.is_premium = True

            result = adapter._parse_user(mock_user)

            assert isinstance(result, TelegramUser)
            assert result.id == 789
            assert result.username == "testuser"
            assert result.first_name == "Test"
            assert result.last_name == "User"
            assert result.language_code == "en"
            assert result.is_bot is False
            assert result.is_premium is True

    def test_telebot_adapter_parse_chat(self):
        """Test TelebotAdapter _parse_chat method."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_chat = Mock()
            mock_chat.id = 456
            mock_chat.type = "private"
            mock_chat.title = "Test Chat"
            mock_chat.username = "testchat"
            mock_chat.first_name = "Test"
            mock_chat.last_name = "Chat"
            mock_chat.description = "Test description"
            mock_chat.invite_link = "https://t.me/testchat"

            result = adapter._parse_chat(mock_chat)

            assert isinstance(result, TelegramChat)
            assert result.id == 456
            assert result.type == "private"
            assert result.title == "Test Chat"
            assert result.username == "testchat"
            assert result.first_name == "Test"
            assert result.last_name == "Chat"
            assert result.description == "Test description"
            assert result.invite_link == "https://t.me/testchat"

    def test_telebot_adapter_parse_message_all_message_types(self):
        """Test TelebotAdapter _parse_message method for all message types."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            message_types = [
                (MessageType.VOICE, "voice"),
                (MessageType.AUDIO, "audio"),
                (MessageType.DOCUMENT, "document"),
                (MessageType.PHOTO, "photo"),
                (MessageType.VIDEO, "video"),
                (MessageType.STICKER, "sticker"),
                (MessageType.LOCATION, "location"),
                (MessageType.CONTACT, "contact"),
                (MessageType.POLL, "poll"),
            ]

            for expected_type, attr_name in message_types:
                mock_message = Mock()
                mock_message.message_id = 123
                mock_message.chat.id = 456
                mock_message.from_user.id = 789
                mock_message.from_user.username = "testuser"
                mock_message.from_user.first_name = "Test"
                mock_message.from_user.last_name = "User"
                mock_message.from_user.language_code = "en"
                mock_message.from_user.is_bot = False
                mock_message.from_user.is_premium = False
                mock_message.text = None
                mock_message.date = 1234567890
                mock_message.edit_date = None
                mock_message.media_group_id = None
                mock_message.caption = None
                mock_message.entities = None

                for msg_attr in [
                    "voice",
                    "audio",
                    "document",
                    "photo",
                    "video",
                    "sticker",
                    "location",
                    "contact",
                    "poll",
                ]:
                    setattr(
                        mock_message,
                        msg_attr,
                        Mock() if msg_attr == attr_name else None,
                    )

                result = adapter._parse_message(mock_message)

                assert isinstance(result, TelegramMessage)
                assert result.message_type == expected_type

    def test_telebot_adapter_parse_message_none_entities(self):
        """Test TelebotAdapter _parse_message method with None entities."""
        with patch("ttskit.telegram.telebot_adapter.TeleBot") as mock_telebot:
            mock_bot = Mock()
            mock_telebot.return_value = mock_bot

            adapter = TelebotAdapter("test_token")

            mock_message = Mock()
            mock_message.message_id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = "Hello world"
            mock_message.date = 1234567890
            mock_message.edit_date = None
            mock_message.media_group_id = None
            mock_message.caption = None
            mock_message.entities = None

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.entities is None
