"""Comprehensive tests for Telethon adapter."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ttskit.telegram.base import (
    MessageType,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)
from ttskit.telegram.telethon_adapter import TelethonAdapter


class TestTelethonAdapter:
    """Test cases for TelethonAdapter class."""

    def test_telethon_adapter_initialization(self):
        """Test TelethonAdapter initialization."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            assert adapter.bot_token == "test_token"
            assert adapter.api_id == 12345
            assert adapter.api_hash == "test_hash"
            assert not adapter.is_running
            assert adapter._message_handler is None
            assert adapter._callback_handler is None
            assert adapter._error_handler is None

    @pytest.mark.asyncio
    async def test_telethon_adapter_start(self):
        """Test TelethonAdapter start method."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.start = AsyncMock()
            mock_client_instance.run_until_disconnected = AsyncMock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            await adapter.start()

            mock_client_instance.start.assert_called_once_with(bot_token="test_token")
            assert adapter.is_running

    @pytest.mark.asyncio
    async def test_telethon_adapter_start_exception(self):
        """Test TelethonAdapter start method with exception."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.start = AsyncMock(
                side_effect=Exception("Start failed")
            )
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            with pytest.raises(Exception, match="Start failed"):
                await adapter.start()

            assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_telethon_adapter_stop(self, mock_telethon_globally):
        """Test TelethonAdapter stop method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        await adapter.stop()

        mock_client.disconnect.assert_called_once()
        assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_telethon_adapter_stop_exception(self):
        """Test TelethonAdapter stop method with exception."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.disconnect = AsyncMock(
                side_effect=Exception("Stop failed")
            )
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
            adapter._running = True

            await adapter.stop()

            assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_telethon_adapter_send_message(self, mock_telethon_globally):
        """Test TelethonAdapter send_message method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat_id = 456
        mock_message.from_id = Mock()
        mock_message.from_id.id = 789
        mock_message.message = "Hello"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.grouped_id = None
        mock_message.entities = None

        mock_client.send_message.return_value = mock_message

        result = await adapter.send_message(456, "Hello")

        mock_client.send_message.assert_called_once_with(
            entity=456, message="Hello", reply_to=None, parse_mode=None
        )

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.chat_id == 456
        assert result.text == "Hello"

    @pytest.mark.asyncio
    async def test_telethon_adapter_send_message_with_reply(
        self, mock_telethon_globally
    ):
        """Test TelethonAdapter send_message method with reply."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat_id = 456
        mock_message.from_id = Mock()
        mock_message.from_id.id = 789
        mock_message.message = "Reply message"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.grouped_id = None
        mock_message.entities = None

        mock_client.send_message.return_value = mock_message

        result = await adapter.send_message(
            456, "Reply message", reply_to_message_id=10
        )

        mock_client.send_message.assert_called_once_with(
            entity=456, message="Reply message", reply_to=10, parse_mode=None
        )

        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_telethon_adapter_send_message_exception(
        self, mock_telethon_globally
    ):
        """Test TelethonAdapter send_message method with exception."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_client.send_message.side_effect = Exception("Send failed")

        with pytest.raises(Exception, match="Send failed"):
            await adapter.send_message(456, "Hello")

    @pytest.mark.asyncio
    async def test_telethon_adapter_send_voice(self, mock_telethon_globally):
        """Test TelethonAdapter send_voice method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat_id = 456
        mock_message.from_id = Mock()
        mock_message.from_id.id = 789
        mock_message.message = "Voice message"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.grouped_id = None
        mock_message.entities = None

        mock_client.send_file.return_value = mock_message

        result = await adapter.send_voice(456, b"fake_voice_data", "Voice message")

        mock_client.send_file.assert_called_once()
        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_telethon_adapter_send_audio(self, mock_telethon_globally):
        """Test TelethonAdapter send_audio method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat_id = 456
        mock_message.from_id = Mock()
        mock_message.from_id.id = 789
        mock_message.message = "Audio file"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.grouped_id = None
        mock_message.entities = None

        mock_client.send_file.return_value = mock_message

        result = await adapter.send_audio(456, b"fake_audio_data", "Audio file")

        mock_client.send_file.assert_called_once()
        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_telethon_adapter_send_document(self, mock_telethon_globally):
        """Test TelethonAdapter send_document method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat_id = 456
        mock_message.from_id = Mock()
        mock_message.from_id.id = 789
        mock_message.message = "Document"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.grouped_id = None
        mock_message.entities = None

        mock_client.send_file.return_value = mock_message

        result = await adapter.send_document(
            456, b"fake_doc_data", "test.pdf", "Document"
        )

        mock_client.send_file.assert_called_once()
        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_telethon_adapter_edit_message_text(self, mock_telethon_globally):
        """Test TelethonAdapter edit_message_text method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat_id = 456
        mock_message.from_id = Mock()
        mock_message.from_id.id = 789
        mock_message.message = "Edited text"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.grouped_id = None
        mock_message.entities = None

        mock_client.edit_message.return_value = mock_message

        result = await adapter.edit_message_text(456, 123, "Edited text")

        mock_client.edit_message.assert_called_once_with(
            entity=456, message=123, text="Edited text", parse_mode=None
        )

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.text == "Edited text"

    @pytest.mark.asyncio
    async def test_telethon_adapter_delete_message(self, mock_telethon_globally):
        """Test TelethonAdapter delete_message method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_client.delete_messages.return_value = True

        result = await adapter.delete_message(456, 123)

        mock_client.delete_messages.assert_called_once_with(456, 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_telethon_adapter_delete_message_exception(self):
        """Test TelethonAdapter delete_message method with exception."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.delete_messages = AsyncMock(
                side_effect=Exception("Delete failed")
            )
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            result = await adapter.delete_message(456, 123)

            assert result is False

    @pytest.mark.asyncio
    async def test_telethon_adapter_get_chat(self, mock_telethon_globally):
        """Test TelethonAdapter get_chat method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_chat = Mock()
        mock_chat.id = 456
        mock_chat.__class__.__name__ = "Chat"
        mock_chat.title = "Test Chat"
        mock_chat.username = "testchat"
        mock_chat.first_name = "Test"
        mock_chat.last_name = "Chat"
        mock_chat.about = "Test description"
        mock_chat.invite_link = "https://t.me/testchat"

        mock_client.get_entity.return_value = mock_chat

        result = await adapter.get_chat(456)

        mock_client.get_entity.assert_called_once_with(456)

        assert isinstance(result, TelegramChat)
        assert result.id == 456
        assert result.type == "chat"
        assert result.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_telethon_adapter_get_user(self, mock_telethon_globally):
        """Test TelethonAdapter get_user method."""
        mock_client_class, mock_client = mock_telethon_globally

        adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True
        adapter.client = mock_client

        mock_user = Mock()
        mock_user.id = 789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.lang_code = "en"
        mock_user.bot = False
        mock_user.premium = True

        mock_client.get_entity.return_value = mock_user

        result = await adapter.get_user(789)

        mock_client.get_entity.assert_called_once_with(789)

        assert isinstance(result, TelegramUser)
        assert result.id == 789
        assert result.username == "testuser"
        assert result.is_premium is True

    def test_telethon_adapter_set_handlers(self):
        """Test TelethonAdapter handler setting."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

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

    def test_telethon_adapter_parse_message_text(self):
        """Test TelethonAdapter _parse_message method for text message."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.lang_code = "en"
            mock_user.bot = False
            mock_user.premium = False

            class MockMessage:
                def __init__(self):
                    self.id = 123
                    self.chat_id = 456
                    self.from_id = mock_user
                    self.sender_id = 789  # Add sender_id attribute
                    self.sender = mock_user  # Add sender attribute
                    self.message = "Hello world"
                    self.date = None
                    self.edit_date = None
                    self.grouped_id = None
                    self.entities = None
                    self.reply_to_msg_id = None
                    self.voice = None
                    self.audio = None
                    self.document = None
                    self.photo = None
                    self.video = None
                    self.sticker = None
                    self.location = None
                    self.contact = None
                    self.poll = None
                    self.geo = None

            mock_message = MockMessage()

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.chat_id == 456
            assert result.text == "Hello world"
            assert result.message_type == MessageType.TEXT

    def test_telethon_adapter_parse_message_voice(self):
        """Test TelethonAdapter _parse_message method for voice message."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.lang_code = "en"
            mock_user.bot = False
            mock_user.premium = False

            mock_message = Mock()
            mock_message.id = 123
            mock_message.chat_id = 456
            mock_message.from_id = mock_user
            mock_message.message = "Voice message"
            mock_message.date = None
            mock_message.edit_date = None
            mock_message.grouped_id = None
            mock_message.entities = None
            mock_message.voice = Mock()

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.message_type == MessageType.VOICE

    def test_telethon_adapter_parse_message_with_reply(self):
        """Test TelethonAdapter _parse_message method with reply."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.lang_code = "en"
            mock_user.bot = False
            mock_user.premium = False

            mock_message = Mock()
            mock_message.id = 123
            mock_message.chat_id = 456
            mock_message.from_id = mock_user
            mock_message.message = "Reply message"
            mock_message.reply_to_msg_id = 10
            mock_message.date = None
            mock_message.edit_date = None
            mock_message.grouped_id = None
            mock_message.entities = None

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.reply_to_message_id == 10

    def test_telethon_adapter_parse_message_with_entities(self):
        """Test TelethonAdapter _parse_message method with entities."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.lang_code = "en"
            mock_user.bot = False
            mock_user.premium = False

            mock_entity1 = Mock()
            mock_entity1.__dict__ = {"type": "bold", "offset": 0, "length": 5}
            mock_entity2 = Mock()
            mock_entity2.__dict__ = {"type": "italic", "offset": 6, "length": 5}

            mock_message = Mock()
            mock_message.id = 123
            mock_message.chat_id = 456
            mock_message.from_id = mock_user
            mock_message.message = "Hello world"
            mock_message.date = None
            mock_message.edit_date = None
            mock_message.grouped_id = None
            mock_message.entities = [mock_entity1, mock_entity2]

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.entities == [
                {"type": "bold", "offset": 0, "length": 5},
                {"type": "italic", "offset": 6, "length": 5},
            ]

    def test_telethon_adapter_parse_user(self):
        """Test TelethonAdapter _parse_user method."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.lang_code = "en"
            mock_user.bot = False
            mock_user.premium = True

            result = adapter._parse_user(mock_user)

            assert isinstance(result, TelegramUser)
            assert result.id == 789
            assert result.username == "testuser"
            assert result.first_name == "Test"
            assert result.last_name == "User"
            assert result.language_code == "en"
            assert result.is_bot is False
            assert result.is_premium is True

    def test_telethon_adapter_parse_chat(self):
        """Test TelethonAdapter _parse_chat method."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_chat = Mock()
            mock_chat.id = 456
            mock_chat.__class__.__name__ = "Channel"
            mock_chat.title = "Test Channel"
            mock_chat.username = "testchannel"
            mock_chat.first_name = "Test"
            mock_chat.last_name = "Channel"
            mock_chat.about = "Test description"
            mock_chat.invite_link = "https://t.me/testchannel"

            result = adapter._parse_chat(mock_chat)

            assert isinstance(result, TelegramChat)
            assert result.id == 456
            assert result.type == "channel"
            assert result.title == "Test Channel"
            assert result.username == "testchannel"
            assert result.first_name == "Test"
            assert result.last_name == "Channel"
            assert result.description == "Test description"
            assert result.invite_link == "https://t.me/testchannel"

    def test_telethon_adapter_parse_message_none_user(self):
        """Test TelethonAdapter _parse_message method with None user."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_message = Mock()
            mock_message.id = 123
            mock_message.chat_id = 456
            mock_message.from_id = None
            mock_message.sender_id = None  # Add sender_id as None
            mock_message.sender = None  # Ensure sender is None
            mock_message.message = "Hello world"
            mock_message.date = None
            mock_message.edit_date = None
            mock_message.grouped_id = None
            mock_message.entities = None

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.id == 123
            assert result.user is None

    def test_telethon_adapter_parse_message_all_message_types(self):
        """Test TelethonAdapter _parse_message method for all message types."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            message_types = [
                (MessageType.VOICE, "voice"),
                (MessageType.AUDIO, "audio"),
                (MessageType.DOCUMENT, "document"),
                (MessageType.PHOTO, "photo"),
                (MessageType.VIDEO, "video"),
                (MessageType.STICKER, "sticker"),
                (MessageType.LOCATION, "geo"),
                (MessageType.CONTACT, "contact"),
                (MessageType.POLL, "poll"),
            ]

            for expected_type, attr_name in message_types:
                mock_user = Mock()
                mock_user.id = 789
                mock_user.username = "testuser"
                mock_user.first_name = "Test"
                mock_user.last_name = "User"
                mock_user.lang_code = "en"
                mock_user.bot = False
                mock_user.premium = False

                mock_message = Mock()
                mock_message.id = 123
                mock_message.chat_id = 456
                mock_message.from_id = mock_user
                mock_message.message = "Test message"
                mock_message.date = None
                mock_message.edit_date = None
                mock_message.grouped_id = None
                mock_message.entities = None

                for msg_attr in [
                    "voice",
                    "audio",
                    "document",
                    "photo",
                    "video",
                    "sticker",
                    "geo",
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

    def test_telethon_adapter_parse_message_caption_for_non_text(self):
        """Test TelethonAdapter _parse_message method caption for non-text messages."""
        with patch("ttskit.telegram.telethon_adapter.TelegramClient") as mock_client:
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            adapter = TelethonAdapter("test_token", api_id=12345, api_hash="test_hash")

            mock_user = Mock()
            mock_user.id = 789
            mock_user.username = "testuser"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.lang_code = "en"
            mock_user.bot = False
            mock_user.premium = False

            mock_message = Mock()
            mock_message.id = 123
            mock_message.chat_id = 456
            mock_message.from_id = mock_user
            mock_message.message = "Voice caption"
            mock_message.date = None
            mock_message.edit_date = None
            mock_message.grouped_id = None
            mock_message.entities = None
            mock_message.voice = Mock()

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.message_type == MessageType.VOICE
            assert result.caption == "Voice caption"
