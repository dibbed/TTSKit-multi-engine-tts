"""Comprehensive tests for Pyrogram adapter."""

from unittest.mock import Mock, patch

import pytest

from ttskit.telegram.base import (
    MessageType,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)
from ttskit.telegram.pyrogram_adapter import PyrogramAdapter


@pytest.fixture(scope="function")
def mock_pyrogram_globally():
    """Mock Pyrogram globally for testing."""

    mock_client_class = Mock()
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    async def async_start():
        return None

    async def async_stop():
        return None

    async def async_send_message(*args, **kwargs):
        return Mock()

    async def async_send_voice(*args, **kwargs):
        return Mock()

    async def async_send_audio(*args, **kwargs):
        return Mock()

    async def async_send_document(*args, **kwargs):
        return Mock()

    async def async_edit_message_text(*args, **kwargs):
        return Mock()

    async def async_delete_messages(*args, **kwargs):
        return True

    async def async_get_chat(*args, **kwargs):
        return Mock()

    async def async_get_users(*args, **kwargs):
        return Mock()

    mock_client.start = async_start
    mock_client.stop = async_stop
    mock_client.send_message = async_send_message
    mock_client.send_voice = async_send_voice
    mock_client.send_audio = async_send_audio
    mock_client.send_document = async_send_document
    mock_client.edit_message_text = async_edit_message_text
    mock_client.delete_messages = async_delete_messages
    mock_client.get_chat = async_get_chat
    mock_client.get_users = async_get_users

    with patch("ttskit.telegram.pyrogram_adapter.Client", mock_client_class):
        yield mock_client_class, mock_client


def _setup_mock_for_start(mock_client):
    """Helper function to setup mock client for start operations."""
    pass


class TestPyrogramAdapter:
    """Test cases for PyrogramAdapter class."""

    def test_pyrogram_adapter_initialization(self, mock_pyrogram_globally):
        """Test PyrogramAdapter initialization."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        assert adapter.bot_token == "test_token"
        assert adapter.api_id == 12345
        assert adapter.api_hash == "test_hash"
        assert not adapter.is_running
        assert adapter._message_handler is None
        assert adapter._callback_handler is None
        assert adapter._error_handler is None

    def test_pyrogram_adapter_initialization_minimal(self, mock_pyrogram_globally):
        """Test PyrogramAdapter initialization with minimal parameters."""
        adapter = PyrogramAdapter("test_token")

        assert adapter.bot_token == "test_token"
        assert adapter.api_id is None
        assert adapter.api_hash is None
        assert not adapter.is_running

    def test_pyrogram_adapter_initialization_with_client(self, mock_pyrogram_globally):
        """Test PyrogramAdapter initialization with injected client."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter(
            "test_token", api_id=12345, api_hash="test_hash", client=mock_client
        )

        assert adapter.bot_token == "test_token"
        assert adapter.api_id == 12345
        assert adapter.api_hash == "test_hash"
        assert adapter.client == mock_client
        assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_start(self, mock_pyrogram_globally):
        """Test PyrogramAdapter start method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        # The actual implementation uses a session file path, not in-memory session
        # Get the actual path that was used in the call
        actual_call_args = mock_client_class.call_args
        assert actual_call_args is not None
        session_path = actual_call_args[0][0]  # First positional argument
        assert session_path.endswith("pyrogram_ttskit_bot")
        assert "data" in session_path and "sessions" in session_path
        assert actual_call_args[1] == {
            "api_id": 12345,
            "api_hash": "test_hash",
            "bot_token": "test_token",
        }
        assert adapter.is_running
        assert adapter.client == mock_client

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_start_exception(self, mock_pyrogram_globally):
        """Test PyrogramAdapter start method with exception."""
        mock_client_class, mock_client = mock_pyrogram_globally

        async def failing_start():
            raise Exception("Start failed")

        mock_client.start = failing_start
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        with pytest.raises(Exception):
            await adapter.start()

        assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_start_with_injected_client(
        self, mock_pyrogram_globally
    ):
        """Test PyrogramAdapter start method with injected client."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter(
            "test_token", api_id=12345, api_hash="test_hash", client=mock_client
        )

        await adapter.start()

        mock_client_class.assert_not_called()
        assert adapter.is_running
        assert adapter.client == mock_client

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_stop(self, mock_pyrogram_globally):
        """Test PyrogramAdapter stop method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True

        await adapter.start()
        await adapter.stop()

        assert not adapter.is_running

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_stop_exception(self, mock_pyrogram_globally):
        """Test PyrogramAdapter stop method with exception."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")
        adapter._running = True

        await adapter.start()

        async def failing_stop():
            raise Exception("Stop failed")

        adapter.client.stop = failing_stop

        await adapter.stop()

        assert adapter.is_running

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_send_message(self, mock_pyrogram_globally):
        """Test PyrogramAdapter send_message method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = "Hello"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = None
        mock_message.entities = None

        async def mock_send_message(*args, **kwargs):
            return mock_message

        adapter.client.send_message = mock_send_message

        result = await adapter.send_message(456, "Hello")

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.chat_id == 456
        assert result.text == "Hello"

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_send_message_with_reply(
        self, mock_pyrogram_globally
    ):
        """Test PyrogramAdapter send_message method with reply."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = "Reply message"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = None
        mock_message.entities = None

        async def mock_send_message(*args, **kwargs):
            return mock_message

        adapter.client.send_message = mock_send_message

        result = await adapter.send_message(
            456, "Reply message", reply_to_message_id=10
        )

        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_send_message_exception(
        self, mock_pyrogram_globally
    ):
        """Test PyrogramAdapter send_message method with exception."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        async def failing_send_message(*args, **kwargs):
            raise Exception("Send failed")

        adapter.client.send_message = failing_send_message

        with pytest.raises(Exception):
            await adapter.send_message(456, "Hello")

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_send_voice(self, mock_pyrogram_globally):
        """Test PyrogramAdapter send_voice method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = None
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = "Voice message"
        mock_message.entities = None

        async def mock_send_voice(*args, **kwargs):
            return mock_message

        adapter.client.send_voice = mock_send_voice

        result = await adapter.send_voice(456, b"fake_voice_data", "Voice message")

        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_send_audio(self, mock_pyrogram_globally):
        """Test PyrogramAdapter send_audio method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = None
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = "Audio file"
        mock_message.entities = None

        async def mock_send_audio(*args, **kwargs):
            return mock_message

        adapter.client.send_audio = mock_send_audio

        result = await adapter.send_audio(456, b"fake_audio_data", "Audio file")

        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_send_document(self, mock_pyrogram_globally):
        """Test PyrogramAdapter send_document method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = None
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = "Document"
        mock_message.entities = None

        async def mock_send_document(*args, **kwargs):
            return mock_message

        adapter.client.send_document = mock_send_document

        result = await adapter.send_document(
            456, b"fake_doc_data", "test.pdf", "Document"
        )

        assert isinstance(result, TelegramMessage)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_edit_message_text(self, mock_pyrogram_globally):
        """Test PyrogramAdapter edit_message_text method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = "Edited text"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = None
        mock_message.entities = None

        async def mock_edit_message_text(*args, **kwargs):
            return mock_message

        adapter.client.edit_message_text = mock_edit_message_text

        result = await adapter.edit_message_text(456, 123, "Edited text")

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.text == "Edited text"

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_delete_message(self, mock_pyrogram_globally):
        """Test PyrogramAdapter delete_message method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        async def mock_delete_messages(*args, **kwargs):
            return True

        adapter.client.delete_messages = mock_delete_messages

        result = await adapter.delete_message(456, 123)

        assert result is True

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_delete_message_exception(
        self, mock_pyrogram_globally
    ):
        """Test PyrogramAdapter delete_message method with exception."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        async def failing_delete_messages(*args, **kwargs):
            raise Exception("Delete failed")

        adapter.client.delete_messages = failing_delete_messages

        result = await adapter.delete_message(456, 123)

        assert result is False

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_get_chat(self, mock_pyrogram_globally):
        """Test PyrogramAdapter get_chat method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_chat = Mock()
        mock_chat.id = 456
        mock_chat.type = "private"
        mock_chat.title = "Test Chat"
        mock_chat.username = "testchat"
        mock_chat.first_name = "Test"
        mock_chat.last_name = "Chat"
        mock_chat.description = "Test description"
        mock_chat.invite_link = "https://t.me/testchat"

        async def mock_get_chat(*args, **kwargs):
            return mock_chat

        adapter.client.get_chat = mock_get_chat

        result = await adapter.get_chat(456)

        assert isinstance(result, TelegramChat)
        assert result.id == 456
        assert result.type == "private"
        assert result.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_pyrogram_adapter_get_user(self, mock_pyrogram_globally):
        """Test PyrogramAdapter get_user method."""
        mock_client_class, mock_client = mock_pyrogram_globally
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        await adapter.start()

        mock_user = Mock()
        mock_user.id = 789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        mock_user.is_bot = False
        mock_user.is_premium = True

        async def mock_get_users(*args, **kwargs):
            return mock_user

        adapter.client.get_users = mock_get_users

        result = await adapter.get_user(789)

        assert isinstance(result, TelegramUser)
        assert result.id == 789
        assert result.username == "testuser"
        assert result.is_premium is True

    def test_pyrogram_adapter_set_handlers(self, mock_pyrogram_globally):
        """Test PyrogramAdapter handler setting."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

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

    def test_pyrogram_adapter_parse_message_text(self, mock_pyrogram_globally):
        """Test PyrogramAdapter _parse_message method for text message."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = "Hello world"
        mock_message.voice = None
        mock_message.audio = None
        mock_message.document = None
        mock_message.photo = None
        mock_message.video = None
        mock_message.sticker = None
        mock_message.location = None
        mock_message.contact = None
        mock_message.poll = None
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = None
        mock_message.entities = None

        result = adapter._parse_message(mock_message)

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.chat_id == 456
        assert result.text == "Hello world"
        assert result.message_type == MessageType.TEXT

    def test_pyrogram_adapter_parse_message_voice(self, mock_pyrogram_globally):
        """Test PyrogramAdapter _parse_message method for voice message."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = None
        mock_message.voice = Mock()
        mock_message.audio = None
        mock_message.document = None
        mock_message.photo = None
        mock_message.video = None
        mock_message.sticker = None
        mock_message.location = None
        mock_message.contact = None
        mock_message.poll = None
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = "Voice message"
        mock_message.entities = None

        result = adapter._parse_message(mock_message)

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.message_type == MessageType.VOICE
        assert result.caption == "Voice message"

    def test_pyrogram_adapter_parse_message_with_entities(self, mock_pyrogram_globally):
        """Test PyrogramAdapter _parse_message method with entities."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        mock_entity1 = Mock()
        mock_entity1.__dict__ = {"type": "bold", "offset": 0, "length": 5}
        mock_entity2 = Mock()
        mock_entity2.__dict__ = {"type": "italic", "offset": 6, "length": 5}

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = "Hello world"
        mock_message.date = None
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

    def test_pyrogram_adapter_parse_user(self, mock_pyrogram_globally):
        """Test PyrogramAdapter _parse_user method."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

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

    def test_pyrogram_adapter_parse_chat(self, mock_pyrogram_globally):
        """Test PyrogramAdapter _parse_chat method."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

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

    def test_pyrogram_adapter_parse_message_none_user(self, mock_pyrogram_globally):
        """Test PyrogramAdapter _parse_message method with None user."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user = None
        mock_message.text = "Hello world"
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = None
        mock_message.entities = None

        result = adapter._parse_message(mock_message)

        assert isinstance(result, TelegramMessage)
        assert result.id == 123
        assert result.user is None

    def test_pyrogram_adapter_parse_message_all_message_types(
        self, mock_pyrogram_globally
    ):
        """Test PyrogramAdapter _parse_message method for all message types."""
        adapter = PyrogramAdapter("test_token", api_id=12345, api_hash="test_hash")

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
            mock_message.id = 123
            mock_message.chat.id = 456
            mock_message.from_user.id = 789
            mock_message.from_user.username = "testuser"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.from_user.language_code = "en"
            mock_message.from_user.is_bot = False
            mock_message.from_user.is_premium = False
            mock_message.text = None
            mock_message.date = None
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
                    mock_message, msg_attr, Mock() if msg_attr == attr_name else None
                )

            result = adapter._parse_message(mock_message)

            assert isinstance(result, TelegramMessage)
            assert result.message_type == expected_type
