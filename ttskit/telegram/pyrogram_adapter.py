"""Pyrogram adapter for TTSKit.

Provides integration with the Pyrogram client library for Telegram bots,
supporting session management, media sending, and event handling in an
async-friendly manner. Designed for use with TTSKit's unified interface.
"""

from pathlib import Path
from typing import Optional

from pyrogram import Client
from pyrogram.types import Chat, Message, User

from ..config import settings
from ..utils.logging_config import get_logger
from .base import (
    MessageType,
    TelegramAdapter,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
)

logger = get_logger(__name__)


class PyrogramAdapter(TelegramAdapter):
    """Pyrogram adapter implementation for TTSKit.

    Handles Telegram bot operations using Pyrogram's MTProto client,
    including authentication, sending media, and basic event routing.

    Notes:
        Requires API ID and hash for initialization; supports injected clients for testing.
        Uses in-memory sessions to avoid file persistence.
    """

    def __init__(
        self,
        bot_token: str,
        api_id: int | None = None,
        api_hash: str | None = None,
        client: Optional[Client] = None,
    ):
        """Initialize the adapter with Pyrogram credentials and optional client.

        Args:
            bot_token: The Telegram bot token.
            api_id: Telegram API ID (required unless client provided).
            api_hash: Telegram API hash (required unless client provided).
            client: Optional pre-existing Pyrogram Client for testing.

        Raises:
            ValueError: If required credentials missing without client.
        """
        super().__init__(bot_token)
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = client  # Allow injection of client for testing
        self._message_handler = None
        self._callback_handler = None
        self._error_handler = None

    async def start(self) -> None:
        """Initialize and start the Pyrogram client session.

        Creates a new client if none provided and connects using bot token.

        Notes:
            Configures in-memory session and disables automatic updates/polling.

        Raises:
            Exception: If client creation or start fails (e.g., invalid credentials).
        """
        try:
            if self.client is None:
                # Use a persistent, namespaced session under settings.session_path
                session_dir = Path(settings.session_path).resolve()
                session_dir.mkdir(parents=True, exist_ok=True)
                session_name = str(session_dir / "pyrogram_ttskit_bot")
                try:
                    self.client = Client(
                        session_name,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        bot_token=self.bot_token,
                    )
                    await self.client.start()
                    logger.info("[Pyrogram] Client started with file-based session")
                except Exception as e:
                    # Fallback: if sqlite session path is not writable, use in-memory session
                    if "unable to open database file" in str(e).lower():
                        logger.warning(
                            "Pyrogram session file path not writable. Falling back to in-memory session."
                        )
                        self.client = Client(
                            "pyrogram_ttskit_bot",
                            api_id=self.api_id,
                            api_hash=self.api_hash,
                            bot_token=self.bot_token,
                            in_memory=True,
                        )
                        await self.client.start()
                        logger.info("[Pyrogram] Client started with in-memory session")
                    else:
                        raise
            else:
                await self.client.start()
                logger.info("[Pyrogram] Client started (pre-initialized)")

            # Start receiving updates by running idle() in background (once for all cases)
            import asyncio

            from pyrogram import idle

            # Setup message handlers
            self._setup_handlers()

            # Start receiving updates by running idle() in background

            # Use get_event_loop() to avoid "already running" error
            loop = asyncio.get_event_loop()
            loop.create_task(idle())
            logger.info("[Pyrogram] Started receiving updates (idle mode)")
            self._running = True
            logger.info("Pyrogram bot started")
        except Exception as e:
            logger.error(f"Failed to start Pyrogram bot: {e}")
            raise

    async def stop(self) -> None:
        """Disconnect and stop the Pyrogram client.

        Notes:
            Calls client.stop() if initialized; always resets running state.

        Raises:
            Exception: If disconnection fails.
        """
        try:
            if self.client is not None:
                await self.client.stop()
            self._running = False
            logger.info("Pyrogram bot stopped")
        except Exception as e:
            logger.error(f"Failed to stop Pyrogram bot: {e}")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None,
    ) -> TelegramMessage:
        """Send a plain text message to the chat.

        Args:
            chat_id: The target chat ID.
            text: The message content.
            reply_to_message_id: Optional reply target ID.
            parse_mode: Optional parsing mode (e.g., 'html').

        Returns:
            The sent message as a parsed TelegramMessage.

        Raises:
            Exception: If sending fails.
        """
        try:
            self._ensure_client()
            message = await self.client.send_message(
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
        """Send a voice note using in-memory buffer.

        Args:
            chat_id: The target chat ID.
            voice_data: Voice audio bytes (OGG assumed).
            caption: Optional caption.
            reply_to_message_id: Optional reply ID.
            duration: Optional duration in seconds.

        Returns:
            The sent voice as a parsed TelegramMessage.

        Raises:
            Exception: If upload fails.

        Notes:
            Uses BytesIO for file-like object.
        """
        try:
            self._ensure_client()
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
                    logger.info(f"[Pyrogram] Calculated duration: {duration}s")
                except Exception as dur_error:
                    logger.warning(
                        f"[Pyrogram] Could not calculate duration: {dur_error}, using default 5s"
                    )
                    duration = 5

            message = await self.client.send_voice(
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
        """Send an audio file with optional metadata.

        Args:
            chat_id: The target chat ID.
            audio_data: Audio bytes (MP3 assumed).
            caption: Optional caption.
            reply_to_message_id: Optional reply ID.
            title: Optional title.
            performer: Optional performer.
            duration: Optional duration.

        Returns:
            The sent audio as a parsed TelegramMessage.

        Raises:
            Exception: If sending fails.

        Notes:
            Uses BytesIO and sets MP3 filename.
        """
        try:
            self._ensure_client()
            from io import BytesIO

            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.mp3"

            message = await self.client.send_audio(
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
        """Send a document file using in-memory buffer.

        Args:
            chat_id: The target chat ID.
            document_data: Document bytes.
            filename: The file name with extension.
            caption: Optional caption.
            reply_to_message_id: Optional reply ID.

        Returns:
            The sent document as a parsed TelegramMessage.

        Raises:
            Exception: If upload fails.

        Notes:
            Uses BytesIO for efficient sending without temp files.
        """
        try:
            self._ensure_client()
            from io import BytesIO

            doc_file = BytesIO(document_data)
            doc_file.name = filename

            message = await self.client.send_document(
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
        """Edit the text of an existing message.

        Args:
            chat_id: The chat ID.
            message_id: The message ID.
            text: New text content.
            parse_mode: Optional parsing mode.

        Returns:
            The edited message as parsed.

        Raises:
            Exception: If edit fails.
        """
        try:
            self._ensure_client()
            message = await self.client.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode
            )
            return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            raise

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete the specified message.

        Args:
            chat_id: The chat ID.
            message_id: The message ID.

        Returns:
            True on success, False on failure.

        Notes:
            Uses delete_messages for single ID.
        """
        try:
            self._ensure_client()
            await self.client.delete_messages(chat_id=chat_id, message_ids=message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    async def get_chat(self, chat_id: int) -> TelegramChat:
        """Fetch chat details via get_chat.

        Args:
            chat_id: The chat ID.

        Returns:
            Parsed TelegramChat.

        Raises:
            Exception: If retrieval fails.
        """
        try:
            self._ensure_client()
            chat = await self.client.get_chat(chat_id)
            return self._parse_chat(chat)
        except Exception as e:
            logger.error(f"Failed to get chat: {e}")
            raise

    async def get_user(self, user_id: int) -> TelegramUser:
        """Fetch user details via get_users.

        Args:
            user_id: The user ID.

        Returns:
            Parsed TelegramUser.

        Raises:
            Exception: If retrieval fails.
        """
        try:
            self._ensure_client()
            user = await self.client.get_users(user_id)
            return self._parse_user(user)
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise

    def set_message_handler(self, handler) -> None:
        """Register message processing handler.

        Args:
            handler: Async callable for messages.

        Notes:
            Not used in this adapter's polling-less setup; for compatibility.
        """
        self._message_handler = handler

    def set_callback_handler(self, handler) -> None:
        """Register callback handler.

        Args:
            handler: Async callable for callbacks.

        Notes:
            For compatibility; manual invocation needed in custom event loops.
        """
        self._callback_handler = handler

    def set_error_handler(self, handler) -> None:
        """Register error handling callback.

        Args:
            handler: Async callable for exceptions.

        Notes:
            For compatibility in error scenarios.
        """
        self._error_handler = handler

    def _setup_handlers(self) -> None:
        """Register message and callback handlers for Pyrogram.

        Uses Pyrogram decorators to handle incoming messages and callbacks.
        """
        from pyrogram import filters

        @self.client.on_message(filters.text)
        async def handle_message(client, message):
            if self._message_handler:
                try:
                    parsed_message = self._parse_message(message)
                    await self._message_handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in Pyrogram message handler: {e}")
                    if self._error_handler:
                        await self._error_handler(e, message)

        @self.client.on_callback_query()
        async def handle_callback(client, callback_query):
            if self._callback_handler:
                try:
                    parsed_message = self._parse_callback(callback_query)
                    await self._callback_handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in Pyrogram callback handler: {e}")
                    if self._error_handler:
                        await self._error_handler(e, callback_query)

    def _parse_callback(self, callback_query) -> TelegramMessage:
        """Convert Pyrogram CallbackQuery to standardized TelegramMessage.

        Args:
            callback_query: The Pyrogram CallbackQuery object.

        Returns:
            Parsed TelegramMessage with callback data as text.
        """
        return TelegramMessage(
            id=callback_query.id,
            chat_id=callback_query.message.chat.id if callback_query.message else 0,
            user=self._parse_user(callback_query.from_user)
            if callback_query.from_user
            else None,
            text=callback_query.data,
            message_type=MessageType.TEXT,
            reply_to_message_id=None,
            date=callback_query.message.date.timestamp()
            if callback_query.message and callback_query.message.date
            else None,
            edit_date=None,
            media_group_id=None,
            caption=None,
            entities=None,
            raw_data=callback_query.__dict__,
        )

    def _ensure_client(self) -> None:
        """Verify the client is started before operations.

        Raises:
            RuntimeError: If client not initialized (call start() first).
        """
        if self.client is None:
            raise RuntimeError("Client not initialized. Call start() first.")

    def _parse_message(self, message: Message) -> TelegramMessage:
        """Convert Pyrogram Message to standardized TelegramMessage.

        Extracts user, type, timestamps, and entities.

        Args:
            message: The Pyrogram Message object.

        Returns:
            Parsed TelegramMessage with all fields.

        Notes:
            Detects types: TEXT, VOICE, AUDIO, DOCUMENT, PHOTO, VIDEO,
            STICKER, LOCATION, CONTACT, POLL. Uses __dict__ for raw data.
            Handles optional from_user and timestamps.
        """
        user = self._parse_user(message.from_user) if message.from_user else None

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

        return TelegramMessage(
            id=message.id,
            chat_id=message.chat.id,
            user=user,
            text=message.text,
            message_type=message_type,
            reply_to_message_id=message.reply_to_message.id
            if message.reply_to_message
            else None,
            date=message.date.timestamp() if message.date else None,
            edit_date=message.edit_date.timestamp() if message.edit_date else None,
            media_group_id=message.media_group_id,
            caption=message.caption,
            entities=[entity.__dict__ for entity in message.entities]
            if message.entities
            else None,
            raw_data=message.__dict__,
        )

    def _parse_user(self, user: User) -> TelegramUser:
        """Convert Pyrogram User to standardized format.

        Args:
            user: The Pyrogram User.

        Returns:
            TelegramUser with fields mapped, is_premium default False.
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
        """Convert Pyrogram Chat to standardized format.

        Args:
            chat: The Pyrogram Chat.

        Returns:
            TelegramChat with core attributes.
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
