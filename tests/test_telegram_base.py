"""Comprehensive tests for Telegram base classes."""

from ttskit.telegram.base import (
    BaseTelegramAdapter,
    MessageType,
    TelegramAdapter,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)


class TestMessageType:
    """Test cases for MessageType enum."""

    def test_message_type_values(self):
        """Test MessageType enum values."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.VOICE.value == "voice"
        assert MessageType.AUDIO.value == "audio"
        assert MessageType.DOCUMENT.value == "document"
        assert MessageType.PHOTO.value == "photo"
        assert MessageType.VIDEO.value == "video"
        assert MessageType.STICKER.value == "sticker"
        assert MessageType.LOCATION.value == "location"
        assert MessageType.CONTACT.value == "contact"
        assert MessageType.POLL.value == "poll"
        assert MessageType.UNKNOWN.value == "unknown"

    def test_message_type_enumeration(self):
        """Test MessageType enumeration."""
        types = list(MessageType)
        assert len(types) == 11
        assert MessageType.TEXT in types
        assert MessageType.VOICE in types
        assert MessageType.AUDIO in types
        assert MessageType.DOCUMENT in types
        assert MessageType.PHOTO in types
        assert MessageType.VIDEO in types
        assert MessageType.STICKER in types
        assert MessageType.LOCATION in types
        assert MessageType.CONTACT in types
        assert MessageType.POLL in types
        assert MessageType.UNKNOWN in types


class TestTelegramUser:
    """Test cases for TelegramUser dataclass."""

    def test_telegram_user_creation(self):
        """Test TelegramUser creation with minimal data."""
        user = TelegramUser(id=123456789)

        assert user.id == 123456789
        assert user.username is None
        assert user.first_name is None
        assert user.last_name is None
        assert user.language_code is None
        assert user.is_bot is False
        assert user.is_premium is False

    def test_telegram_user_creation_with_all_fields(self):
        """Test TelegramUser creation with all fields."""
        user = TelegramUser(
            id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="en",
            is_bot=False,
            is_premium=True,
        )

        assert user.id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.is_bot is False
        assert user.is_premium is True

    def test_telegram_user_bot_user(self):
        """Test TelegramUser for bot user."""
        user = TelegramUser(
            id=987654321,
            username="testbot",
            first_name="Test Bot",
            is_bot=True,
            is_premium=False,
        )

        assert user.id == 987654321
        assert user.username == "testbot"
        assert user.first_name == "Test Bot"
        assert user.is_bot is True
        assert user.is_premium is False

    def test_telegram_user_premium_user(self):
        """Test TelegramUser for premium user."""
        user = TelegramUser(
            id=555666777,
            username="premiumuser",
            first_name="Premium",
            last_name="User",
            language_code="fa",
            is_bot=False,
            is_premium=True,
        )

        assert user.id == 555666777
        assert user.username == "premiumuser"
        assert user.first_name == "Premium"
        assert user.last_name == "User"
        assert user.language_code == "fa"
        assert user.is_bot is False
        assert user.is_premium is True


class TestTelegramMessage:
    """Test cases for TelegramMessage dataclass."""

    def test_telegram_message_creation_minimal(self):
        """Test TelegramMessage creation with minimal data."""
        user = TelegramUser(id=123456789)
        message = TelegramMessage(id=1, chat_id=456789, user=user)

        assert message.id == 1
        assert message.chat_id == 456789
        assert message.user == user
        assert message.text is None
        assert message.message_type == MessageType.TEXT
        assert message.reply_to_message_id is None
        assert message.date is None
        assert message.edit_date is None
        assert message.media_group_id is None
        assert message.caption is None
        assert message.entities is None
        assert message.raw_data is None

    def test_telegram_message_creation_with_text(self):
        """Test TelegramMessage creation with text."""
        user = TelegramUser(id=123456789, username="testuser")
        message = TelegramMessage(
            id=2,
            chat_id=456789,
            user=user,
            text="Hello, world!",
            message_type=MessageType.TEXT,
            date=1234567890,
            edit_date=1234567891,
        )

        assert message.id == 2
        assert message.chat_id == 456789
        assert message.user == user
        assert message.text == "Hello, world!"
        assert message.message_type == MessageType.TEXT
        assert message.date == 1234567890
        assert message.edit_date == 1234567891

    def test_telegram_message_voice_type(self):
        """Test TelegramMessage with voice type."""
        user = TelegramUser(id=123456789)
        message = TelegramMessage(
            id=3,
            chat_id=456789,
            user=user,
            message_type=MessageType.VOICE,
            caption="Voice message",
        )

        assert message.id == 3
        assert message.chat_id == 456789
        assert message.user == user
        assert message.message_type == MessageType.VOICE
        assert message.caption == "Voice message"

    def test_telegram_message_with_entities(self):
        """Test TelegramMessage with entities."""
        user = TelegramUser(id=123456789)
        entities = [
            {"type": "bold", "offset": 0, "length": 5},
            {"type": "italic", "offset": 6, "length": 5},
        ]
        message = TelegramMessage(
            id=4, chat_id=456789, user=user, text="Hello world", entities=entities
        )

        assert message.id == 4
        assert message.text == "Hello world"
        assert message.entities == entities

    def test_telegram_message_reply_to(self):
        """Test TelegramMessage with reply to message."""
        user = TelegramUser(id=123456789)
        message = TelegramMessage(
            id=5,
            chat_id=456789,
            user=user,
            text="This is a reply",
            reply_to_message_id=10,
        )

        assert message.id == 5
        assert message.text == "This is a reply"
        assert message.reply_to_message_id == 10

    def test_telegram_message_with_raw_data(self):
        """Test TelegramMessage with raw data."""
        user = TelegramUser(id=123456789)
        raw_data = {"message_id": 6, "chat": {"id": 456789}, "text": "Raw data"}
        message = TelegramMessage(
            id=6, chat_id=456789, user=user, text="Test message", raw_data=raw_data
        )

        assert message.id == 6
        assert message.text == "Test message"
        assert message.raw_data == raw_data


class TestTelegramChat:
    """Test cases for TelegramChat dataclass."""

    def test_telegram_chat_private(self):
        """Test TelegramChat for private chat."""
        chat = TelegramChat(
            id=123456789, type="private", first_name="Test", last_name="User"
        )

        assert chat.id == 123456789
        assert chat.type == "private"
        assert chat.first_name == "Test"
        assert chat.last_name == "User"
        assert chat.title is None
        assert chat.username is None
        assert chat.description is None
        assert chat.invite_link is None

    def test_telegram_chat_group(self):
        """Test TelegramChat for group chat."""
        chat = TelegramChat(
            id=-987654321,
            type="group",
            title="Test Group",
            description="A test group",
            invite_link="https://t.me/testgroup",
        )

        assert chat.id == -987654321
        assert chat.type == "group"
        assert chat.title == "Test Group"
        assert chat.description == "A test group"
        assert chat.invite_link == "https://t.me/testgroup"
        assert chat.username is None
        assert chat.first_name is None
        assert chat.last_name is None

    def test_telegram_chat_channel(self):
        """Test TelegramChat for channel."""
        chat = TelegramChat(
            id=-1001234567890,
            type="channel",
            title="Test Channel",
            username="testchannel",
            description="A test channel",
        )

        assert chat.id == -1001234567890
        assert chat.type == "channel"
        assert chat.title == "Test Channel"
        assert chat.username == "testchannel"
        assert chat.description == "A test channel"
        assert chat.invite_link is None
        assert chat.first_name is None
        assert chat.last_name is None

    def test_telegram_chat_supergroup(self):
        """Test TelegramChat for supergroup."""
        chat = TelegramChat(
            id=-1009876543210,
            type="supergroup",
            title="Test Supergroup",
            username="testsupergroup",
            description="A test supergroup",
            invite_link="https://t.me/testsupergroup",
        )

        assert chat.id == -1009876543210
        assert chat.type == "supergroup"
        assert chat.title == "Test Supergroup"
        assert chat.username == "testsupergroup"
        assert chat.description == "A test supergroup"
        assert chat.invite_link == "https://t.me/testsupergroup"


class TestTelegramAdapter:
    """Test cases for TelegramAdapter abstract base class."""

    def test_telegram_adapter_initialization(self):
        """Test TelegramAdapter initialization."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        assert adapter.bot_token == "test_token"
        assert not adapter.is_running

    def test_telegram_adapter_is_running_property(self):
        """Test TelegramAdapter is_running property."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                self._running = True

            async def stop(self):
                self._running = False

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        assert not adapter.is_running

        adapter._running = True
        assert adapter.is_running

        adapter._running = False
        assert not adapter.is_running

    def test_telegram_adapter_parse_command_basic(self):
        """Test TelegramAdapter parse_command method with basic command."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("/tts Hello world")

        assert isinstance(result, dict)
        assert "text" in result
        assert "lang" in result
        assert "engine" in result
        assert "voice" in result
        assert "rate" in result
        assert "pitch" in result

        assert result["text"] == "Hello world"
        assert result["lang"] == "en"
        assert result["engine"] is None
        assert result["voice"] is None
        assert result["rate"] == 1.0
        assert result["pitch"] == 0.0

    def test_telegram_adapter_parse_command_empty(self):
        """Test TelegramAdapter parse_command method with empty input."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("")

        assert isinstance(result, dict)
        assert result["text"] == ""
        assert result["lang"] == "en"
        assert result["engine"] is None
        assert result["voice"] is None
        assert result["rate"] == 1.0
        assert result["pitch"] == 0.0

    def test_telegram_adapter_parse_command_with_language(self):
        """Test TelegramAdapter parse_command method with language prefix."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("[fa]: سلام دنیا")

        assert result["text"] == "سلام دنیا"
        assert result["lang"] == "fa"

    def test_telegram_adapter_parse_command_with_engine(self):
        """Test TelegramAdapter parse_command method with engine prefix."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("{edge} Hello world")

        assert result["text"] == "Hello world"
        assert result["engine"] == "edge"

    def test_telegram_adapter_parse_command_with_voice(self):
        """Test TelegramAdapter parse_command method with voice prefix."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("(voice:en-US-AriaNeural) Hello world")

        assert result["text"] == "Hello world"
        assert result["voice"] == "en-US-AriaNeural"

    def test_telegram_adapter_parse_command_with_rate(self):
        """Test TelegramAdapter parse_command method with rate prefix."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("+10% Hello world")

        assert result["text"] == "Hello world"
        assert result["rate"] == 1.1

        result = adapter.parse_command("+2st Hello world")

        assert result["text"] == "Hello world"
        assert result["rate"] == 2 ** (2 / 12.0)

    def test_telegram_adapter_parse_command_with_pitch(self):
        """Test TelegramAdapter parse_command method with pitch prefix."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("@+2st Hello world")

        assert result["text"] == "Hello world"
        assert result["pitch"] == 2.0

        result = adapter.parse_command("@+1.5 Hello world")

        assert result["text"] == "Hello world"
        assert result["pitch"] == 1.5

    def test_telegram_adapter_parse_command_complex(self):
        """Test TelegramAdapter parse_command method with complex command."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command(
            "[fa] {edge} (voice:fa-IR-FaridNeural) +10% @+2st سلام دنیا"
        )

        assert (
            result["text"] == "[fa] {edge} (voice:fa-IR-FaridNeural) 10 2st سلام دنیا"
        )
        assert result["lang"] == "fa"
        assert result["engine"] is None
        assert result["voice"] is None
        assert result["rate"] == 1.0
        assert result["pitch"] == 0.0

    def test_telegram_adapter_parse_command_invalid_prefixes(self):
        """Test TelegramAdapter parse_command method with invalid prefixes."""

        class TestAdapter(TelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

            def set_message_handler(self, handler):
                pass

            def set_callback_handler(self, handler):
                pass

            def set_error_handler(self, handler):
                pass

        adapter = TestAdapter("test_token")

        result = adapter.parse_command("[xx] Hello world")

        assert result["text"] == "[xx] Hello world"
        assert result["lang"] == "en"

        result = adapter.parse_command("{invalid} Hello world")

        assert result["text"] == "Hello world"
        assert result["engine"] is None


class TestBaseTelegramAdapter:
    """Test cases for BaseTelegramAdapter class."""

    def test_base_telegram_adapter_initialization(self):
        """Test BaseTelegramAdapter initialization."""

        class TestBaseAdapter(BaseTelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

        adapter = TestBaseAdapter("test_token")

        assert adapter.bot_token == "test_token"
        assert not adapter.is_running
        assert adapter._message_handler is None
        assert adapter._callback_handler is None
        assert adapter._error_handler is None

    def test_base_telegram_adapter_set_handlers(self):
        """Test BaseTelegramAdapter handler setting."""

        class TestBaseAdapter(BaseTelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

        adapter = TestBaseAdapter("test_token")

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

    def test_base_telegram_adapter_handler_replacement(self):
        """Test BaseTelegramAdapter handler replacement."""

        class TestBaseAdapter(BaseTelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

        adapter = TestBaseAdapter("test_token")

        def handler1(message):
            pass

        def handler2(message):
            pass

        adapter.set_message_handler(handler1)
        assert adapter._message_handler == handler1

        adapter.set_message_handler(handler2)
        assert adapter._message_handler == handler2
        assert adapter._message_handler != handler1

    def test_base_telegram_adapter_handler_none(self):
        """Test BaseTelegramAdapter setting handlers to None."""

        class TestBaseAdapter(BaseTelegramAdapter):
            async def start(self):
                pass

            async def stop(self):
                pass

            async def send_message(
                self, chat_id, text, reply_to_message_id=None, parse_mode=None
            ):
                pass

            async def send_voice(
                self,
                chat_id,
                voice_data,
                caption=None,
                reply_to_message_id=None,
                duration=None,
            ):
                pass

            async def send_audio(
                self,
                chat_id,
                audio_data,
                caption=None,
                reply_to_message_id=None,
                title=None,
                performer=None,
                duration=None,
            ):
                pass

            async def send_document(
                self,
                chat_id,
                document_data,
                filename,
                caption=None,
                reply_to_message_id=None,
            ):
                pass

            async def edit_message_text(
                self, chat_id, message_id, text, parse_mode=None
            ):
                pass

            async def delete_message(self, chat_id, message_id):
                pass

            async def get_chat(self, chat_id):
                pass

            async def get_user(self, user_id):
                pass

        adapter = TestBaseAdapter("test_token")

        def mock_handler(message):
            pass

        adapter.set_message_handler(mock_handler)
        assert adapter._message_handler == mock_handler

        adapter.set_message_handler(None)
        assert adapter._message_handler is None
