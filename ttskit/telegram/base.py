"""Base classes and utilities for Telegram adapters in TTSKit.

This module defines the core abstract base class for Telegram adapters, along
with standardized data models for messages, users, and chats. It also includes
common parsing utilities and command processing logic shared across adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class MessageType(Enum):
    """Enumeration of supported Telegram message types.

    Defines the various types of messages that adapters can handle, such as text,
    media, and interactive elements.
    """

    TEXT = "text"
    VOICE = "voice"
    AUDIO = "audio"
    DOCUMENT = "document"
    PHOTO = "photo"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"
    POLL = "poll"
    UNKNOWN = "unknown"


@dataclass
class TelegramUser:
    """Standardized representation of a Telegram user.

    Captures essential user details for uniform handling across adapters.

    Attributes:
        id: Unique user identifier.
        username: Optional username handle.
        first_name: User's first name.
        last_name: User's last name.
        language_code: Preferred language code.
        is_bot: Whether the user is a bot.
        is_premium: Whether the user has premium status.
    """

    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    is_bot: bool = False
    is_premium: bool = False


@dataclass
class TelegramMessage:
    """Standardized representation of a Telegram message.

    Provides a uniform structure for messages from different adapters, including
    metadata, content, and raw framework data.

    Attributes:
        id: Unique message identifier.
        chat_id: ID of the chat where the message was sent.
        user: The user who sent the message.
        text: Message text content, if applicable.
        message_type: Type of the message (e.g., TEXT, VOICE).
        reply_to_message_id: ID of the message being replied to, if any.
        date: Timestamp when the message was sent.
        edit_date: Timestamp when the message was last edited.
        media_group_id: ID for grouped media messages.
        caption: Caption for media messages.
        entities: List of message entities (e.g., mentions, links).
        raw_data: Original data from the framework.
    """

    id: int
    chat_id: int
    user: TelegramUser
    text: str | None = None
    message_type: MessageType = MessageType.TEXT
    reply_to_message_id: int | None = None
    date: int | None = None
    edit_date: int | None = None
    media_group_id: str | None = None
    caption: str | None = None
    entities: list[dict[str, Any]] | None = None
    raw_data: dict[str, Any] | None = None


@dataclass
class TelegramChat:
    """Standardized representation of a Telegram chat.

    Captures chat details for consistent access across adapters.

    Attributes:
        id: Unique chat identifier.
        type: Type of chat (e.g., 'private', 'group').
        title: Chat title, if applicable.
        username: Chat username handle.
        first_name: First name for private chats.
        last_name: Last name for private chats.
        description: Chat description.
        invite_link: Invite link for the chat.
    """

    id: int
    type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    description: str | None = None
    invite_link: str | None = None


class TelegramAdapter(ABC):
    """Abstract base class defining the interface for Telegram adapters.

    All concrete adapters must implement these methods to provide uniform
    Telegram bot functionality for TTSKit, including sending messages,
    handling events, and managing bot lifecycle.
    """

    def __init__(self, bot_token: str):
        """Initialize the adapter with bot credentials.

        Args:
            bot_token: The Telegram bot token for authentication.
        """
        self.bot_token = bot_token
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start the bot and begin listening for updates.

        This method initializes the bot connection and starts polling or
        other update mechanisms. Subclasses must implement the specific
        startup logic for their framework.

        Raises:
            Any framework-specific exceptions during startup.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the bot and clean up resources.

        This method disconnects the bot and releases any held resources.
        Subclasses must implement the specific shutdown logic.

        Raises:
            Any framework-specific exceptions during shutdown.
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None,
    ) -> TelegramMessage:
        """Send a text message to the specified chat.

        Supports optional replies and text formatting.

        Args:
            chat_id: The target chat identifier.
            text: The content of the message.
            reply_to_message_id: Optional ID of a message to reply to.
            parse_mode: Optional parsing mode for formatted text (e.g., 'HTML', 'Markdown').

        Returns:
            The sent message as a standardized TelegramMessage object.

        Raises:
            Framework-specific errors if sending fails.
        """
        pass

    @abstractmethod
    async def send_voice(
        self,
        chat_id: int,
        voice_data: bytes,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        duration: int | None = None,
    ) -> TelegramMessage:
        """Send a voice message to the chat.

        Handles voice note transmission with optional caption and duration info.

        Args:
            chat_id: The target chat identifier.
            voice_data: Binary data of the voice file (typically OGG format).
            caption: Optional text caption for the voice.
            reply_to_message_id: Optional ID of a message to reply to.
            duration: Optional duration of the voice in seconds.

        Returns:
            The sent voice message as a standardized TelegramMessage object.

        Raises:
            Framework-specific errors if sending fails.
        """
        pass

    @abstractmethod
    async def send_audio(
        self,
        chat_id: int,
        audio_data: bytes,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        title: str | None = None,
        performer: str | None = None,
        duration: int | None = None,
    ) -> TelegramMessage:
        """Send an audio file to the chat.

        Supports metadata like title and performer for better playback.

        Args:
            chat_id: The target chat identifier.
            audio_data: Binary data of the audio file (typically MP3).
            caption: Optional text caption.
            reply_to_message_id: Optional ID of a message to reply to.
            title: Optional title for the audio.
            performer: Optional artist or performer name.
            duration: Optional duration in seconds.

        Returns:
            The sent audio message as a standardized TelegramMessage object.

        Raises:
            Framework-specific errors if sending fails.
        """
        pass

    @abstractmethod
    async def send_document(
        self,
        chat_id: int,
        document_data: bytes,
        filename: str,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> TelegramMessage:
        """Send a document file to the chat.

        Allows attaching files with custom filenames and captions.

        Args:
            chat_id: The target chat identifier.
            document_data: Binary data of the document.
            filename: The name of the file including extension.
            caption: Optional text caption.
            reply_to_message_id: Optional ID of a message to reply to.

        Returns:
            The sent document message as a standardized TelegramMessage object.

        Raises:
            Framework-specific errors if sending fails.
        """
        pass

    @abstractmethod
    async def edit_message_text(
        self, chat_id: int, message_id: int, text: str, parse_mode: str | None = None
    ) -> TelegramMessage:
        """Edit the text content of an existing message.

        Updates the message in place, preserving other attributes.

        Args:
            chat_id: The chat containing the message.
            message_id: The ID of the message to edit.
            text: The new text content.
            parse_mode: Optional parsing mode for the text.

        Returns:
            The edited message as a standardized TelegramMessage object.

        Raises:
            Framework-specific errors if editing fails (e.g., message not found).
        """
        pass

    @abstractmethod
    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a specific message from the chat.

        Args:
            chat_id: The chat containing the message.
            message_id: The ID of the message to delete.

        Returns:
            True if the deletion was successful, False otherwise.

        Raises:
            Framework-specific errors if deletion fails.
        """
        pass

    @abstractmethod
    async def get_chat(self, chat_id: int) -> TelegramChat:
        """Retrieve information about a chat.

        Args:
            chat_id: The identifier of the chat.

        Returns:
            A standardized TelegramChat object with chat details.

        Raises:
            Framework-specific errors if the chat is not accessible.
        """
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> TelegramUser:
        """Retrieve information about a user.

        Args:
            user_id: The identifier of the user.

        Returns:
            A standardized TelegramUser object with user details.

        Raises:
            Framework-specific errors if the user is not accessible.
        """
        pass

    @abstractmethod
    def set_message_handler(self, handler: Callable) -> None:
        """Register a handler for incoming messages.

        Args:
            handler: An async callable that processes TelegramMessage objects.

        Raises:
            TypeError if handler is not callable.
        """
        pass

    @abstractmethod
    def set_callback_handler(self, handler: Callable) -> None:
        """Register a handler for callback queries.

        Args:
            handler: An async callable that processes callback messages.

        Raises:
            TypeError if handler is not callable.
        """
        pass

    @abstractmethod
    def set_error_handler(self, handler) -> None:
        """Register a handler for errors and exceptions.

        Args:
            handler: An async callable that handles exceptions and raw error data.

        Raises:
            TypeError if handler is not callable.
        """
        pass

    @property
    def is_running(self) -> bool:
        """Check the current running status of the bot.

        Returns:
            True if the bot is actively running, False otherwise.
        """
        return self._running

    def _parse_message(self, raw_message: Any) -> TelegramMessage:
        """Parse a raw message from the framework into a standardized format.

        This internal method must be implemented by subclasses to convert
        framework-specific message objects.

        Args:
            raw_message: The raw message object from the underlying framework.

        Returns:
            A standardized TelegramMessage object.

        Raises:
            NotImplementedError if not overridden in subclass.
        """
        raise NotImplementedError

    def _parse_user(self, raw_user: Any) -> TelegramUser:
        """Parse a raw user object from the framework.

        Internal method for subclasses to standardize user data.

        Args:
            raw_user: The raw user object from the framework.

        Returns:
            A standardized TelegramUser object.

        Raises:
            NotImplementedError if not overridden.
        """
        raise NotImplementedError

    def _parse_chat(self, raw_chat: Any) -> TelegramChat:
        """Parse a raw chat object from the framework.

        Internal method for subclasses to standardize chat data.

        Args:
            raw_chat: The raw chat object from the framework.

        Returns:
            A standardized TelegramChat object.

        Raises:
            NotImplementedError if not overridden.
        """
        raise NotImplementedError

    def parse_command(self, raw_text: str) -> dict[str, Any]:
        """Parse TTS command parameters from raw user text.

        Supports prefixes for language, engine, voice, rate, and pitch, along with
        TTS command triggers. Automatically detects RTL languages if not specified
        and cleans text for TTS processing.

        Args:
            raw_text: The raw input text from the user, potentially containing command modifiers.

        Returns:
            A dictionary with parsed parameters:
                - text: Cleaned text to synthesize.
                - lang: Language code (defaults to 'en').
                - engine: TTS engine name, if specified.
                - voice: Voice name, if specified.
                - rate: Speech rate multiplier (defaults to 1.0).
                - pitch: Pitch adjustment (defaults to 0.0).

        Notes:
            Recognizes TTS commands like /tts, /speak, /voice, /صدا, /تکلم.
            Language format: [lang]: text (e.g., [fa]: سلام).
            Engine: {engine} text (e.g., {piper} hello).
            Voice: (voice:name) text.
            Rate: +1.5 text or +20% text or +2st text (semitones).
            Pitch: @0.5 text or @2st text.
            Falls back to English and auto-detects RTL if needed.
        """
        import re

        from ..utils.text import clean_text_for_tts, detect_rtl_language
        from ..utils.validate import (
            validate_engine,
            validate_language,
            validate_pitch,
            validate_rate,
        )

        result = {
            "text": "",
            "lang": "en",
            "engine": None,
            "voice": None,
            "rate": 1.0,
            "pitch": 0.0,
        }

        if not raw_text or not raw_text.strip():
            return result

        text = raw_text.strip()

        tts_commands = ["/tts", "/speak", "/voice", "/صدا", "/تکلم"]
        for command in tts_commands:
            if text.lower().startswith(command):
                text = text[len(command) :].strip()
                break

        lang_match = re.match(r"^\[([a-z]{2})\]:\s*(.*)$", text, re.IGNORECASE)
        if lang_match:
            lang = lang_match.group(1).lower()
            text = lang_match.group(2).strip()
            if validate_language(lang):
                result["lang"] = lang

        engine_match = re.match(r"^\{([a-z]+)\}\s*(.*)$", text, re.IGNORECASE)
        if engine_match:
            engine = engine_match.group(1).lower()
            text = engine_match.group(2).strip()
            if validate_engine(engine):
                result["engine"] = engine

        voice_match = re.match(r"^\(voice:([^)]+)\)\s*(.*)$", text, re.IGNORECASE)
        if voice_match:
            voice = voice_match.group(1).strip()
            text = voice_match.group(2).strip()
            result["voice"] = voice

        rate_match = re.match(r"^([+-]?\d+(?:\.\d+)?(?:%|st)?)\s*(.*)$", text)
        if rate_match:
            rate_str = rate_match.group(1)
            text = rate_match.group(2).strip()

            if rate_str.endswith("%"):
                rate = float(rate_str[:-1]) / 100.0 + 1.0
            elif rate_str.endswith("st"):
                semitones = float(rate_str[:-2])
                rate = 2 ** (semitones / 12.0)
            else:
                rate = float(rate_str)

            if validate_rate(rate):
                result["rate"] = rate

        pitch_match = re.match(r"^@([+-]?\d+(?:\.\d+)?(?:st)?)\s*(.*)$", text)
        if pitch_match:
            pitch_str = pitch_match.group(1)
            text = pitch_match.group(2).strip()

            if pitch_str.endswith("st"):
                pitch = float(pitch_str[:-2])
            else:
                pitch = float(pitch_str)

            if validate_pitch(pitch):
                result["pitch"] = pitch

        if result["lang"] == "en" and not lang_match:
            detected_lang = detect_rtl_language(text)
            if detected_lang:
                result["lang"] = detected_lang

        result["text"] = clean_text_for_tts(text, result["lang"])

        return result


class BaseTelegramAdapter(TelegramAdapter):
    """Concrete base implementation providing common handler management.

    Extends the abstract TelegramAdapter with basic handler registration.
    Subclasses should implement the core bot methods.
    """

    def __init__(self, bot_token: str):
        """Initialize the base adapter.

        Args:
            bot_token: The Telegram bot token.
        """
        super().__init__(bot_token)
        self._message_handler = None
        self._callback_handler = None
        self._error_handler = None

    def set_message_handler(self, handler) -> None:
        """Register a handler for incoming messages.

        Args:
            handler: An async callable to process TelegramMessage objects.
        """
        self._message_handler = handler

    def set_callback_handler(self, handler) -> None:
        """Register a handler for callback queries.

        Args:
            handler: An async callable to process callback messages.
        """
        self._callback_handler = handler

    def set_error_handler(self, handler) -> None:
        """Register a handler for errors.

        Args:
            handler: An async callable to handle exceptions.
        """
        self._error_handler = handler
