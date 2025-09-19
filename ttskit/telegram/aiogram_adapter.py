"""Aiogram v3 adapter for TTSKit.

Integrates the Aiogram framework with TTSKit's Telegram interface, handling
message processing, callbacks, and media sending via asynchronous polling.
Supports both real bots and mock instances for testing.
"""

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

from ..utils.logging_config import get_logger
from .base import (
    MessageType,
    TelegramAdapter,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)

logger = get_logger(__name__)


class AiogramAdapter(TelegramAdapter):
    """Aiogram v3 adapter implementation for TTSKit.

    Bridges Aiogram's async framework to TTSKit's standardized Telegram interface.
    Manages bot lifecycle, event dispatching, and media operations with built-in
    error handling and logging.

    Notes:
        Uses in-memory storage for FSM; supports both live bots and mocks for testing.
    """

    def __init__(self, bot_token: str):
        """Initialize the adapter with bot token and dispatcher setup.

        Args:
            bot_token: The Telegram bot token for authentication.

        Notes:
            Initializes a Dispatcher with MemoryStorage for state management.
        """
        super().__init__(bot_token)
        self.bot = None
        self.dp = Dispatcher(storage=MemoryStorage())
        self._message_handler = None
        self._callback_handler = None
        self._error_handler = None

    async def start(self) -> None:
        """Start the bot, set up handlers, and begin polling for updates.

        Handles real bot initialization and polling, or skips for mocks.

        Notes:
            Distinguishes between real Aiogram Bot instances and mocks.
            Uses async polling if available; sets running state on success.

        Raises:
            Exception: If bot initialization or polling fails.
        """
        try:
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            self._setup_handlers()

            from aiogram import Bot as _RealBot

            try:
                is_real_bot = isinstance(self.bot, _RealBot)
            except TypeError:
                is_real_bot = False

            if is_real_bot and self.bot_token and ":" in self.bot_token:
                start_polling = getattr(self.dp, "start_polling", None)
                if callable(start_polling):
                    result = start_polling(self.bot)
                    if hasattr(result, "__await__"):
                        await result
            self._running = True
            logger.info("Aiogram bot started")
        except Exception as e:
            logger.error(f"Failed to start Aiogram bot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the bot, close sessions, and update running state.

        Safely closes the HTTP session for real bots.

        Notes:
            Checks for real Bot instance before closing; ignores mocks.

        Raises:
            Exception: If session closure fails.
        """
        try:
            if self.bot is not None:
                from aiogram import Bot as _RealBot

                try:
                    is_real_bot = isinstance(self.bot, _RealBot)
                except TypeError:
                    is_real_bot = False

                if is_real_bot:
                    await self.bot.session.close()
            self._running = False
            logger.info("Aiogram bot stopped")
        except Exception as e:
            logger.error(f"Failed to stop Aiogram bot: {e}")

    def _setup_handlers(self) -> None:
        """Register message and callback handlers on the dispatcher.

        Routes incoming events to user handlers with try-except for errors.

        Notes:
            Uses Aiogram decorators for message and callback_query events.
            Logs errors and invokes error handler if set.
        """

        @self.dp.message()
        async def handle_message(message: Message):
            if self._message_handler:
                try:
                    parsed_message = self._parse_message(message)
                    await self._message_handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
                    if self._error_handler:
                        await self._error_handler(e, message)

        @self.dp.callback_query()
        async def handle_callback(callback: CallbackQuery):
            if self._callback_handler:
                try:
                    parsed_message = self._parse_callback(callback)
                    await self._callback_handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in callback handler: {e}")
                    if self._error_handler:
                        await self._error_handler(e, callback)

    def _parse_callback(self, callback: CallbackQuery) -> TelegramMessage:
        """Convert an Aiogram callback query to a standardized message.

        Treats callback data as text content.

        Args:
            callback: The Aiogram CallbackQuery object.

        Returns:
            A TelegramMessage with callback details, using data as text.
        """
        user = self._parse_user(callback.from_user)

        return TelegramMessage(
            id=callback.message.message_id if callback.message else 0,
            chat_id=callback.message.chat.id if callback.message else 0,
            user=user,
            text=callback.data,
            message_type=MessageType.TEXT,
            raw_data=callback.model_dump(),
        )

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None,
    ) -> TelegramMessage:
        """Send a text message to the target chat.

        Supports replies and formatting modes.

        Args:
            chat_id: The identifier of the target chat.
            text: The message content.
            reply_to_message_id: Optional ID to reply to.
            parse_mode: Optional mode like 'HTML' or 'MarkdownV2'.

        Returns:
            The sent message as a parsed TelegramMessage.

        Raises:
            Exception: If sending fails (e.g., network error).
        """
        try:
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id,
                parse_mode=parse_mode,
            )
            message = await result if hasattr(result, "__await__") else result
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def send_voice(
        self,
        chat_id: int,
        voice_data: bytes,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        duration: int | None = None,
    ) -> TelegramMessage:
        """Send a voice note to the chat using buffered input.

        Uses OGG format by default.

        Args:
            chat_id: The target chat ID.
            voice_data: Raw bytes of the voice audio.
            caption: Optional caption text.
            reply_to_message_id: Optional reply target.
            duration: Optional voice length in seconds.

        Returns:
            The sent voice message as a parsed TelegramMessage.

        Raises:
            Exception: If file upload or sending fails.
        """
        try:
            from aiogram.types.input_file import BufferedInputFile

            voice_file = BufferedInputFile(voice_data, filename="voice.ogg")

            # Calculate duration if not provided
            if duration is None:
                try:
                    from ..utils.audio_manager import audio_manager

                    # Use audio_manager to get audio info
                    audio_info = audio_manager.get_audio_info(voice_data)
                    duration = int(audio_info.get("duration", 5))
                    logger.info(f"[Aiogram] Calculated duration: {duration}s")
                except Exception as dur_error:
                    logger.warning(
                        f"[Aiogram] Could not calculate duration: {dur_error}, using default 5s"
                    )
                    duration = 5

            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.send_voice(
                chat_id=chat_id,
                voice=voice_file,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                duration=duration,
            )
            message = await result if hasattr(result, "__await__") else result
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to send voice: {e}")
            raise

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
        """Send an audio file to the chat with metadata support.

        Assumes MP3 format.

        Args:
            chat_id: The target chat ID.
            audio_data: Raw bytes of the audio.
            caption: Optional caption.
            reply_to_message_id: Optional reply target.
            title: Optional track title.
            performer: Optional artist name.
            duration: Optional length in seconds.

        Returns:
            The sent audio message as a parsed TelegramMessage.

        Raises:
            Exception: If file handling or sending fails.
        """
        try:
            from io import BytesIO

            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.mp3"
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                title=title,
                performer=performer,
                duration=duration,
            )
            message = await result if hasattr(result, "__await__") else result
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            raise

    async def send_document(
        self,
        chat_id: int,
        document_data: bytes,
        filename: str,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> TelegramMessage:
        """Send a document file to the chat.

        Uses BytesIO for in-memory file upload.

        Args:
            chat_id: The target chat ID.
            document_data: Raw bytes of the document.
            filename: The file name with extension.
            caption: Optional caption text.
            reply_to_message_id: Optional reply target.

        Returns:
            The sent document as a parsed TelegramMessage.

        Raises:
            Exception: If upload or sending fails.
        """
        try:
            from io import BytesIO

            doc_file = BytesIO(document_data)
            doc_file.name = filename
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.send_document(
                chat_id=chat_id,
                document=doc_file,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
            )
            message = await result if hasattr(result, "__await__") else result
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            raise

    async def edit_message_text(
        self, chat_id: int, message_id: int, text: str, parse_mode: str | None = None
    ) -> TelegramMessage:
        """Edit the text of an existing message in the chat.

        Args:
            chat_id: The chat ID.
            message_id: The message ID to edit.
            text: The updated text content.
            parse_mode: Optional formatting mode.

        Returns:
            The edited message as a parsed TelegramMessage.

        Raises:
            Exception: If edit operation fails.
        """
        try:
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode
            )
            message = await result if hasattr(result, "__await__") else result
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            raise

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message from the chat.

        Args:
            chat_id: The chat ID.
            message_id: The message ID to delete.

        Returns:
            True on success, False on failure.

        Raises:
            No explicit raises; returns False on errors.
        """
        try:
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            if hasattr(result, "__await__"):
                await result
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    async def get_chat(self, chat_id: int) -> TelegramChat:
        """Retrieve details about a specific chat.

        Args:
            chat_id: The chat identifier.

        Returns:
            A parsed TelegramChat object.

        Raises:
            Exception: If chat retrieval fails.
        """
        try:
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            result = self.bot.get_chat(chat_id)
            chat_obj = await result if hasattr(result, "__await__") else result
            return self._parse_chat(chat_obj)
        except Exception as e:
            logger.error(f"Failed to get chat: {e}")
            raise

    async def get_user(self, user_id: int) -> TelegramUser:
        """Retrieve user details, trying chat member first then direct chat.

        Args:
            user_id: The user identifier.

        Returns:
            A parsed TelegramUser object.

        Raises:
            Exception: If both methods fail.
        """
        try:
            if self.bot is None:
                self.bot = Bot(token=self.bot_token)
            try:
                result = self.bot.get_chat_member(user_id, user_id)
                member = await result if hasattr(result, "__await__") else result
                return self._parse_user(member.user)
            except Exception:
                result = self.bot.get_chat(user_id)
                user = await result if hasattr(result, "__await__") else result
                return self._parse_user(user)
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise

    def set_message_handler(self, handler) -> None:
        """Set the callback for processing incoming messages.

        Args:
            handler: An async function taking a TelegramMessage.

        Notes:
            Invoked by the dispatcher on new messages.
        """
        self._message_handler = handler

    def set_callback_handler(self, handler) -> None:
        """Set the callback for handling inline button presses.

        Args:
            handler: An async function taking a parsed callback message.

        Notes:
            Processes CallbackQuery events.
        """
        self._callback_handler = handler

    def set_error_handler(self, handler) -> None:
        """Set the callback for error events.

        Args:
            handler: An async function taking exception and raw event.

        Notes:
            Called on handler exceptions with logging.
        """
        self._error_handler = handler

    def _parse_message(self, message: Message) -> TelegramMessage:
        """Convert an Aiogram Message to the standardized TelegramMessage format.

        Determines type based on content and extracts timestamps, entities, etc.

        Args:
            message: The Aiogram Message object to parse.

        Returns:
            A fully populated TelegramMessage with type detection and metadata.

        Notes:
            Supports TEXT, VOICE, AUDIO, DOCUMENT, PHOTO, VIDEO, STICKER,
            LOCATION, CONTACT, POLL types. Handles timestamps flexibly and
            serializes entities/raw data safely.
        """
        user = self._parse_user(message.from_user)

        message_type = MessageType.TEXT
        if message.voice:
            message_type = MessageType.VOICE
        elif message.audio:
            message_type = MessageType.AUDIO
        elif message.document:
            message_type = MessageType.DOCUMENT
        elif message.photo:
            message_type = MessageType.PHOTO
        elif message.video:
            message_type = MessageType.VIDEO
        elif message.sticker:
            message_type = MessageType.STICKER
        elif message.location:
            message_type = MessageType.LOCATION
        elif message.contact:
            message_type = MessageType.CONTACT
        elif message.poll:
            message_type = MessageType.POLL

        def _to_ts(dt):
            try:
                return (
                    dt.timestamp()
                    if hasattr(dt, "timestamp")
                    else (dt if isinstance(dt, int | float) else None)
                )
            except Exception:
                return None

        return TelegramMessage(
            id=message.message_id,
            chat_id=message.chat.id,
            user=user,
            text=message.text,
            message_type=message_type,
            reply_to_message_id=message.reply_to_message.message_id
            if message.reply_to_message
            else None,
            date=_to_ts(message.date) if getattr(message, "date", None) else None,
            edit_date=_to_ts(message.edit_date)
            if getattr(message, "edit_date", None)
            else None,
            media_group_id=message.media_group_id,
            caption=message.caption,
            entities=(
                [
                    (
                        entity.model_dump()
                        if hasattr(entity, "model_dump")
                        else dict(entity)
                    )
                    for entity in message.entities
                ]
                if getattr(message, "entities", None)
                and isinstance(message.entities, list)
                else None
            ),
            raw_data=(message.model_dump() if hasattr(message, "model_dump") else {}),
        )

    def _parse_user(self, user: User) -> TelegramUser:
        """Convert an Aiogram User to the standardized format.

        Args:
            user: The Aiogram User object.

        Returns:
            A TelegramUser with all available fields, defaulting is_premium to False.
        """
        return TelegramUser(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            is_bot=user.is_bot,
            is_premium=getattr(user, "is_premium", False),
        )

    def _parse_chat(self, chat: Chat) -> TelegramChat:
        """Convert an Aiogram Chat to the standardized format.

        Args:
            chat: The Aiogram Chat object.

        Returns:
            A TelegramChat with core fields populated.
        """
        return TelegramChat(
            id=chat.id,
            type=chat.type,
            title=chat.title,
            username=chat.username,
            first_name=chat.first_name,
            last_name=chat.last_name,
            description=chat.description,
            invite_link=chat.invite_link,
        )
