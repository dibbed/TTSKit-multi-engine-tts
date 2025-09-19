"""Telethon adapter for TTSKit.

Integrates the Telethon MTProto library for advanced Telegram client operations,
supporting bot tokens, media uploads via send_file, and entity resolution.
Compatible with TTSKit's async interface.
"""

from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import Chat

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


class TelethonAdapter(TelegramAdapter):
    """Telethon adapter implementation for TTSKit.

    Uses Telethon's full Telegram client for bot operations, requiring API credentials.
    Handles sending via send_message/send_file and entity fetching.

    Notes:
        Initializes client on start; supports voice notes as files with voice_note=True.
        For audio, builds DocumentAttributeAudio manually.
    """

    def __init__(self, bot_token: str, api_id: int, api_hash: str):
        """Initialize with required API credentials.

        Args:
            bot_token: The bot token.
            api_id: Telegram API ID.
            api_hash: Telegram API hash.

        Raises:
            ValueError: If credentials invalid.
        """
        super().__init__(bot_token)
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None  # Will be initialized when needed
        self._message_handler = None
        self._callback_handler = None
        self._error_handler = None

    async def start(self) -> None:
        """Create and start the Telethon client session.

        Uses bot_token for authentication.

        Notes:
            Session named 'ttskit_bot'; no updates polling.

        Raises:
            Exception: If client start fails.
        """
        try:
            if self.client is None:
                # Ensure session directory exists and use namespaced session name to avoid conflicts
                session_dir = Path(settings.session_path)
                session_dir.mkdir(parents=True, exist_ok=True)
                session_name = str(session_dir / "telethon_ttskit_bot")
                self.client = TelegramClient(session_name, self.api_id, self.api_hash)
            await self.client.start(bot_token=self.bot_token)
            self._running = True

            # Start receiving updates by running run_until_disconnected in background
            import asyncio

            # Setup message handlers
            self._setup_handlers()

            # Start receiving updates by running run_until_disconnected in background

            # Use get_event_loop() to avoid "already running" error
            loop = asyncio.get_event_loop()
            loop.create_task(self.client.run_until_disconnected())
            logger.info("Telethon bot started and receiving updates")
        except Exception as e:
            logger.error(f"Failed to start Telethon bot: {e}")
            raise

    async def stop(self) -> None:
        """Disconnect the Telethon client.

        Calls disconnect() and resets state.

        Raises:
            Exception: If disconnect fails.
        """
        try:
            if self.client is not None:
                await self.client.disconnect()
            self._running = False
            logger.info("Telethon bot stopped")
        except Exception as e:
            logger.error(f"Failed to stop Telethon bot: {e}")

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        parse_mode: str | None = None,
    ) -> TelegramMessage:
        """Send text using entity resolution.

        Args:
            chat_id: Target entity ID.
            text: Message text.
            reply_to_message_id: Optional reply ID.
            parse_mode: Optional mode.

        Returns:
            Parsed sent message.

        Raises:
            Exception: If send fails.
        """
        try:
            self._ensure_client()
            message = await self.client.send_message(
                entity=chat_id,
                message=text,
                reply_to=reply_to_message_id,
                parse_mode=parse_mode,
            )
            # Don't try to parse string messages
            if isinstance(message, str):
                logger.info(
                    f"[Telethon] Sent message is string, not parsing: {message}"
                )
                return None
            else:
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
        """Send voice as file with voice_note flag.

        Args:
            chat_id: Target entity.
            voice_data: Voice bytes (OGG).
            caption: Optional caption.
            reply_to_message_id: Optional reply.
            duration: Optional duration.

        Returns:
            Parsed message.

        Raises:
            Exception: If send_file fails.

        Notes:
            Uses send_file with voice_note=True.
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
                    logger.info(f"[Telethon] Calculated duration: {duration}s")
                except Exception as dur_error:
                    logger.warning(
                        f"[Telethon] Could not calculate duration: {dur_error}, using default 5s"
                    )
                    duration = 5

            message = await self.client.send_file(
                entity=chat_id,
                file=voice_file,
                caption=caption,
                reply_to=reply_to_message_id,
                voice_note=True,
                duration=duration,
            )
            # Don't try to parse string messages
            if isinstance(message, str):
                logger.info(f"[Telethon] Sent voice is string, not parsing: {message}")
                return None
            else:
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
        """Send audio file with custom attributes.

        Args:
            chat_id: Target entity.
            audio_data: Audio bytes (MP3).
            caption: Optional caption.
            reply_to_message_id: Optional reply.
            title: Optional title.
            performer: Optional performer.
            duration: Optional duration.

        Returns:
            Parsed message.

        Raises:
            Exception: If send_file fails.

        Notes:
            Uses _build_audio_attribute for metadata; send_file for upload.
        """
        try:
            self._ensure_client()
            from io import BytesIO

            audio_file = BytesIO(audio_data)
            audio_file.name = "audio.mp3"

            message = await self.client.send_file(
                entity=chat_id,
                file=audio_file,
                caption=caption,
                reply_to=reply_to_message_id,
                attributes=[
                    self.client._build_audio_attribute(title, performer, duration)
                ],
            )
            # Don't try to parse string messages
            if isinstance(message, str):
                logger.info(f"[Telethon] Sent audio is string, not parsing: {message}")
                return None
            else:
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
        """Send document as file.

        Args:
            chat_id: Target entity.
            document_data: Document bytes.
            filename: File name.
            caption: Optional caption.
            reply_to_message_id: Optional reply.

        Returns:
            Parsed message.

        Raises:
            Exception: If send_file fails.

        Notes:
            Uses BytesIO for in-memory upload.
        """
        try:
            self._ensure_client()
            from io import BytesIO

            doc_file = BytesIO(document_data)
            doc_file.name = filename

            message = await self.client.send_file(
                entity=chat_id,
                file=doc_file,
                caption=caption,
                reply_to=reply_to_message_id,
            )
            # Don't try to parse string messages
            if isinstance(message, str):
                logger.info(
                    f"[Telethon] Sent document is string, not parsing: {message}"
                )
                return None
            else:
                return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            raise

    async def edit_message_text(
        self, chat_id: int, message_id: int, text: str, parse_mode: str | None = None
    ) -> TelegramMessage:
        """Edit message text via edit_message.

        Args:
            chat_id: Entity ID.
            message_id: Message ID.
            text: New text.
            parse_mode: Optional mode.

        Returns:
            Parsed edited message.

        Raises:
            Exception: If edit fails.
        """
        try:
            self._ensure_client()
            message = await self.client.edit_message(
                entity=chat_id, message=message_id, text=text, parse_mode=parse_mode
            )
            # Don't try to parse string messages
            if isinstance(message, str):
                logger.info(
                    f"[Telethon] Edited message is string, not parsing: {message}"
                )
                return None
            else:
                return self._parse_message(message)
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            raise

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete message using delete_messages.

        Args:
            chat_id: Entity ID.
            message_id: Message ID.

        Returns:
            True on success, False on failure.

        Notes:
            Passes single ID as list-like.
        """
        try:
            self._ensure_client()
            await self.client.delete_messages(chat_id, message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    async def get_chat(self, chat_id: int) -> TelegramChat:
        """Get entity as chat.

        Args:
            chat_id: Entity ID.

        Returns:
            Parsed TelegramChat.

        Raises:
            Exception: If get_entity fails.
        """
        try:
            self._ensure_client()
            chat = await self.client.get_entity(chat_id)
            return self._parse_chat(chat)
        except Exception as e:
            logger.error(f"Failed to get chat: {e}")
            raise

    async def get_user(self, user_id: int) -> TelegramUser:
        """Get entity as user.

        Args:
            user_id: Entity ID.

        Returns:
            Parsed TelegramUser.

        Raises:
            Exception: If get_entity fails.
        """
        try:
            self._ensure_client()
            user = await self.client.get_entity(user_id)
            return self._parse_user(user)
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise

    def set_message_handler(self, handler) -> None:
        """Set message handler (compatibility).

        Args:
            handler: Async callable.

        Notes:
            For API compatibility; manual use in event handlers.
        """
        self._message_handler = handler

    def set_callback_handler(self, handler) -> None:
        """Set callback handler (compatibility).

        Args:
            handler: Async callable.

        Notes:
            For API; manual invocation needed.
        """
        self._callback_handler = handler

    def set_error_handler(self, handler) -> None:
        """Set error handler (compatibility).

        Args:
            handler: Async callable.

        Notes:
            For API; use in error contexts.
        """
        self._error_handler = handler

    def _setup_handlers(self) -> None:
        """Register message and callback handlers for Telethon.

        Uses Telethon event handlers to process incoming messages and callbacks.
        """
        from telethon import events

        @self.client.on(events.NewMessage)
        async def handle_message(event):
            if self._message_handler:
                try:
                    parsed_message = self._parse_message(event)
                    await self._message_handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in Telethon message handler: {e}")
                    if self._error_handler:
                        await self._error_handler(e, event.message)

        @self.client.on(events.CallbackQuery)
        async def handle_callback(event):
            if self._callback_handler:
                try:
                    parsed_message = self._parse_callback(event)
                    await self._callback_handler(parsed_message)
                except Exception as e:
                    logger.error(f"Error in Telethon callback handler: {e}")
                    if self._error_handler:
                        await self._error_handler(e, event)

    def _parse_callback(self, event) -> TelegramMessage:
        """Convert Telethon CallbackQuery event to standardized TelegramMessage.

        Args:
            event: The Telethon CallbackQuery event.

        Returns:
            Parsed TelegramMessage with callback data as text.
        """
        return TelegramMessage(
            id=event.id if event.id is not None else 0,
            chat_id=event.chat_id if event.chat_id else 0,
            user=self._parse_user(event.sender_id) if event.sender_id else None,
            text=event.data.decode() if event.data else "",
            message_type=MessageType.TEXT,
            reply_to_message_id=None,
            date=event.date.timestamp() if event.date else None,
            edit_date=None,
            media_group_id=None,
            caption=None,
            entities=None,
            raw_data=event.__dict__,
        )

    def _ensure_client(self) -> None:
        """Check client initialization.

        Raises:
            RuntimeError: If not started.
        """
        if self.client is None:
            raise RuntimeError("Client not initialized. Call start() first.")

    def _parse_message(self, event) -> TelegramMessage:
        """Convert Telethon Event to standard format.

        Args:
            event: The Telethon NewMessage Event or Message object.

        Returns:
            Parsed TelegramMessage.

        Notes:
            Types: TEXT, VOICE, AUDIO, DOCUMENT, PHOTO, VIDEO, STICKER,
            LOCATION (geo), CONTACT, POLL. Caption from message if non-text.
            Uses event.sender_id for user, grouped_id for media groups.
        """
        # Handle case where event is already a Message object
        if hasattr(event, "message") and not isinstance(event.message, str):
            message = event.message
        else:
            # If event is itself a Message object or string
            message = event

        # If message is a string, we can't process it properly
        if isinstance(message, str):
            logger.error(f"Cannot process string message: {message}")
            raise ValueError(f"Cannot process string message: {message}")

        # In Telethon, event.sender_id is just an int, we need to get the actual User object
        # Let's try to get the user from the event or client
        user = None
        if event.sender_id:
            try:
                # Try to get user from event.sender (if available)
                if hasattr(event, "sender") and event.sender:
                    user = self._parse_user(event.sender)
                else:
                    # Fallback: create a minimal user from sender_id
                    # We'll handle this in _parse_user
                    user = self._parse_user(event.sender_id)
            except Exception:
                logger.error("Failed to get user in _parse_message")
                user = None

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
        elif message.geo:
            message_type = MessageType.LOCATION
        elif message.contact:
            message_type = MessageType.CONTACT
        elif message.poll:
            message_type = MessageType.POLL

        try:
            result = TelegramMessage(
                id=message.id if message.id is not None else 0,
                chat_id=message.chat_id if message.chat_id is not None else 0,
                user=user,
                text=message.message,
                message_type=message_type,
                reply_to_message_id=message.reply_to_msg_id,
                date=message.date.timestamp() if message.date else None,
                edit_date=message.edit_date.timestamp() if message.edit_date else None,
                media_group_id=getattr(message, "grouped_id", None),
                caption=getattr(message, "message", None)
                if message_type != MessageType.TEXT
                else None,
                entities=[entity.__dict__ for entity in message.entities]
                if message.entities
                else None,
                raw_data=message.__dict__,
            )
            return result
        except Exception:
            logger.error("Failed to create TelegramMessage")
            raise

    def _parse_user(self, user) -> TelegramUser:
        """Convert Telethon User or user_id to standard.

        Args:
            user: The Telethon User object or user_id (int).

        Returns:
            TelegramUser; lang_code to language_code, bot to is_bot, premium default False.
        """
        # Handle case where user is just an int (user_id)
        if isinstance(user, int):
            return TelegramUser(
                id=user,
                username=None,
                first_name=None,
                last_name=None,
                language_code=None,
                is_bot=False,
                is_premium=False,
            )

        # Handle case where user is None
        if user is None:
            return TelegramUser(
                id=0,
                username=None,
                first_name=None,
                last_name=None,
                language_code=None,
                is_bot=False,
                is_premium=False,
            )

        # Handle case where user is a User object
        try:
            return TelegramUser(
                id=user.id if user.id is not None else 0,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.lang_code,
                is_bot=user.bot,
                is_premium=getattr(user, "premium", False),
            )
        except Exception:
            logger.error("Failed to parse User object")
            # Fallback to minimal user
            return TelegramUser(
                id=0,
                username=None,
                first_name=None,
                last_name=None,
                language_code=None,
                is_bot=False,
                is_premium=False,
            )

    def _parse_chat(self, chat: Chat) -> TelegramChat:
        """Convert Telethon Chat to standard.

        Args:
            chat: The Telethon Chat or User entity.

        Returns:
            TelegramChat; type from class name, about to description.

        Notes:
            Handles various entity types (Channel, User, etc.) via getattr.
        """
        return TelegramChat(
            id=chat.id if chat.id is not None else 0,
            type=chat.__class__.__name__.lower(),
            title=getattr(chat, "title", None),
            username=getattr(chat, "username", None),
            first_name=getattr(chat, "first_name", None),
            last_name=getattr(chat, "last_name", None),
            description=getattr(chat, "about", None),
            invite_link=getattr(chat, "invite_link", None),
        )
