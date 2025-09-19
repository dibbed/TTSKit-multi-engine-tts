"""PyTelegramBotAPI (telebot) adapter for TTSKit.

Integrates the synchronous Telebot library with TTSKit's async Telegram interface
by running polling in a background thread and scheduling async handlers on the event loop.
Supports message and callback handling with error logging.
"""

import asyncio

from telebot import TeleBot
from telebot.types import CallbackQuery, Chat, Message, User

from ..utils.logging_config import get_logger
from .base import (
    MessageType,
    TelegramAdapter,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)

logger = get_logger(__name__)


class TelebotAdapter(TelegramAdapter):
    """Telebot adapter implementation for TTSKit.

    Wraps the synchronous PyTelegramBotAPI library, using threaded polling
    to bridge to async TTSKit handlers via run_coroutine_threadsafe.

    Notes:
        Captures the running event loop for scheduling; falls back to create_task if needed.
        Daemon thread for non-blocking polling.
    """

    def __init__(self, bot_token: str):
        """Initialize the adapter with Telebot instance.

        Args:
            bot_token: The Telegram bot token.
        """
        super().__init__(bot_token)
        self.bot = TeleBot(bot_token)
        self._message_handler = None
        self._callback_handler = None
        self._error_handler = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        """Start polling in a background thread and set up handlers.

        Captures the event loop for async scheduling.

        Notes:
            Uses daemon thread for infinity_polling with timeouts.
            Sets running state after thread start.

        Raises:
            Exception: If setup or threading fails.
        """
        try:
            self._setup_handlers()
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

            import threading

            def _run_polling():
                try:
                    self.bot.infinity_polling(timeout=20, long_polling_timeout=20)
                except Exception as ex:
                    logger.error(f"Telebot polling error: {ex}")

            threading.Thread(target=_run_polling, daemon=True).start()
            self._running = True
            logger.info("Telebot started (background polling thread)")
        except Exception as e:
            logger.error(f"Failed to start Telebot: {e}")
            raise

    async def stop(self) -> None:
        """Stop polling and reset state.

        Calls stop_polling() and forces running to False.

        Raises:
            Exception: If stop fails, but state is still updated.
        """
        try:
            self.bot.stop_polling()
            self._running = False
            logger.info("Telebot stopped")
        except Exception as e:
            logger.error(f"Failed to stop Telebot: {e}")
            self._running = False

    def _setup_handlers(self) -> None:
        """Register Telebot handlers for messages and callbacks.

        Uses decorators to catch all events, then schedules async handlers
        cross-thread using run_coroutine_threadsafe or create_task.

        Notes:
            Message handler: Catches all messages.
            Callback handler: Catches all callback queries, parses to message-like.
            Falls back to get_running_loop if no captured loop.
            Logs scheduling errors if no loop available.
        """

        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message: Message):
            if self._message_handler:
                try:
                    parsed_message = self._parse_message(message)
                    if self._loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            self._message_handler(parsed_message), self._loop
                        )
                    else:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self._message_handler(parsed_message))
                        except RuntimeError:
                            logger.error("No running loop to schedule message handler")
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
                    if self._error_handler:
                        if self._loop is not None:
                            asyncio.run_coroutine_threadsafe(
                                self._error_handler(e, message), self._loop
                            )
                        else:
                            try:
                                loop = asyncio.get_running_loop()
                                loop.create_task(self._error_handler(e, message))
                            except RuntimeError:
                                logger.error(
                                    "No running loop to schedule error handler"
                                )

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call: CallbackQuery):
            if self._callback_handler:
                try:
                    parsed_message = self._parse_callback(call)
                    if self._loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            self._callback_handler(parsed_message), self._loop
                        )
                    else:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self._callback_handler(parsed_message))
                        except RuntimeError:
                            logger.error("No running loop to schedule callback handler")
                except Exception as e:
                    logger.error(f"Error in callback handler: {e}")
                    if self._error_handler:
                        if self._loop is not None:
                            asyncio.run_coroutine_threadsafe(
                                self._error_handler(e, call), self._loop
                            )
                        else:
                            try:
                                loop = asyncio.get_running_loop()
                                loop.create_task(self._error_handler(e, call))
                            except RuntimeError:
                                logger.error(
                                    "No running loop to schedule error handler"
                                )

    def _parse_callback(self, call: CallbackQuery) -> TelegramMessage:
        """Parse a callback query into a message-like object.

        Uses callback data as text; defaults IDs to 0 if no message.

        Args:
            call: The Telebot CallbackQuery.

        Returns:
            A TelegramMessage representing the callback.
        """
        user = self._parse_user(call.from_user)

        return TelegramMessage(
            id=call.message.message_id if call.message else 0,
            chat_id=call.message.chat.id if call.message else 0,
            user=user,
            text=call.data,
            message_type=MessageType.TEXT,
            raw_data=call.__dict__,
        )

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None,
    ) -> TelegramMessage:
        """Send a synchronous text message via Telebot.

        Args:
            chat_id: The target chat ID.
            text: The message content.
            reply_to_message_id: Optional reply ID.
            parse_mode: Optional parsing (e.g., 'Markdown').

        Returns:
            Parsed sent message.

        Raises:
            Exception: If send fails.
        """
        try:
            message = self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id,
                parse_mode=parse_mode,
            )
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
        """Send a voice message using BytesIO buffer.

        Args:
            chat_id: The target chat ID.
            voice_data: Voice bytes (OGG assumed).
            caption: Optional caption.
            reply_to_message_id: Optional reply ID.
            duration: Optional duration.

        Returns:
            Parsed sent message.

        Raises:
            Exception: If send fails.

        Notes:
            Sets OGG filename for voice note.
        """
        try:
            from io import BytesIO

            voice_file = BytesIO(voice_data)
            voice_file.name = "voice.ogg"

            # Calculate duration if not provided
            if duration is None:
                try:
                    from ..utils.audio_manager import audio_manager

                    # Use audio_manager to get audio info
                    audio_info = audio_manager.get_audio_info(voice_data)
                    duration = int(audio_info.get("duration", 5))
                    logger.info(f"[Telebot] Calculated duration: {duration}s")
                except Exception as dur_error:
                    logger.warning(
                        f"[Telebot] Could not calculate duration: {dur_error}, using default 5s"
                    )
                    duration = 5

            message = self.bot.send_voice(
                chat_id=chat_id,
                voice=voice_file,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                duration=duration,
            )
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
        """Send an audio file with metadata.

        Args:
            chat_id: The target chat ID.
            audio_data: Audio bytes (MP3 assumed).
            caption: Optional caption.
            reply_to_message_id: Optional reply ID.
            title: Optional title.
            performer: Optional performer.
            duration: Optional duration.

        Returns:
            Parsed sent message.

        Raises:
            Exception: If send fails.

        Notes:
            Uses BytesIO with MP3 filename.
        """
        try:
            from io import BytesIO

            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.mp3"

            message = self.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                title=title,
                performer=performer,
                duration=duration,
            )
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
        """Send a document using BytesIO.

        Args:
            chat_id: The target chat ID.
            document_data: Document bytes.
            filename: File name with extension.
            caption: Optional caption.
            reply_to_message_id: Optional reply ID.

        Returns:
            Parsed sent message.

        Raises:
            Exception: If send fails.
        """
        try:
            from io import BytesIO

            doc_file = BytesIO(document_data)
            doc_file.name = filename

            message = self.bot.send_document(
                chat_id=chat_id,
                document=doc_file,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
            )
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            raise

    async def edit_message_text(
        self, chat_id: int, message_id: int, text: str, parse_mode: str | None = None
    ) -> TelegramMessage:
        """Edit message text synchronously.

        Args:
            chat_id: The chat ID.
            message_id: The message ID.
            text: New text.
            parse_mode: Optional mode.

        Returns:
            Parsed edited message.

        Raises:
            Exception: If edit fails.
        """
        try:
            message = self.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode
            )
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            raise

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message synchronously.

        Args:
            chat_id: The chat ID.
            message_id: The message ID.

        Returns:
            True on success, False on failure.
        """
        try:
            self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    async def get_chat(self, chat_id: int) -> TelegramChat:
        """Get chat info synchronously.

        Args:
            chat_id: The chat ID.

        Returns:
            Parsed TelegramChat.

        Raises:
            Exception: If get fails.
        """
        try:
            chat = self.bot.get_chat(chat_id)
            return self._parse_chat(chat)
        except Exception as e:
            logger.error(f"Failed to get chat: {e}")
            raise

    async def get_user(self, user_id: int) -> TelegramUser:
        """Get user info via get_chat (for users).

        Args:
            user_id: The user ID.

        Returns:
            Parsed TelegramUser.

        Raises:
            Exception: If get fails.
        """
        try:
            user = self.bot.get_chat(user_id)
            return self._parse_user(user)
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise

    def set_message_handler(self, handler) -> None:
        """Set message handler for threaded scheduling.

        Args:
            handler: Async callable for messages.
        """
        self._message_handler = handler

    def set_callback_handler(self, handler) -> None:
        """Set callback handler for threaded scheduling.

        Args:
            handler: Async callable for callbacks.
        """
        self._callback_handler = handler

    def set_error_handler(self, handler) -> None:
        """Set error handler for threaded scheduling.

        Args:
            handler: Async callable for errors.
        """
        self._error_handler = handler

    def _parse_message(self, message: Message) -> TelegramMessage:
        """Convert Telebot Message to standardized format.

        Uses getattr for safe attribute access.

        Args:
            message: The Telebot Message.

        Returns:
            Parsed TelegramMessage.

        Notes:
            Type detection uses getattr for optional attrs: VOICE, AUDIO, etc.
            Entities and raw data via __dict__.
        """
        user = self._parse_user(message.from_user)

        message_type = MessageType.TEXT
        if getattr(message, "voice", None):
            message_type = MessageType.VOICE
        elif getattr(message, "audio", None):
            message_type = MessageType.AUDIO
        elif getattr(message, "document", None):
            message_type = MessageType.DOCUMENT
        elif getattr(message, "photo", None):
            message_type = MessageType.PHOTO
        elif getattr(message, "video", None):
            message_type = MessageType.VIDEO
        elif getattr(message, "sticker", None):
            message_type = MessageType.STICKER
        elif getattr(message, "location", None):
            message_type = MessageType.LOCATION
        elif getattr(message, "contact", None):
            message_type = MessageType.CONTACT
        elif getattr(message, "poll", None):
            message_type = MessageType.POLL

        return TelegramMessage(
            id=message.message_id,
            chat_id=message.chat.id,
            user=user,
            text=message.text,
            message_type=message_type,
            reply_to_message_id=(
                message.reply_to_message.message_id
                if getattr(message, "reply_to_message", None)
                else None
            ),
            date=message.date,
            edit_date=message.edit_date,
            media_group_id=message.media_group_id,
            caption=message.caption,
            entities=[entity.__dict__ for entity in message.entities]
            if message.entities
            else None,
            raw_data=message.__dict__,
        )

    def _parse_user(self, user: User) -> TelegramUser:
        """Convert Telebot User to standard format.

        Args:
            user: The Telebot User.

        Returns:
            TelegramUser, with is_premium default False.
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
        """Convert Telebot Chat to standard format.

        Args:
            chat: The Telebot Chat.

        Returns:
            TelegramChat with fields mapped.
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
