"""
Unified TTS Bot for TTSKit.

This module implements a flexible bot that integrates with any Telegram framework
and TTS engine, including smart routing, caching, and full message handling.
"""

import asyncio
from typing import Any

from ..config import settings
from ..engines import factory as engines_factory_module
from ..engines import registry as engines_registry
from ..engines.smart_router import SmartRouter
from ..exceptions import AllEnginesFailedError, EngineNotFoundError
from ..telegram.base import TelegramAdapter, TelegramMessage
from ..telegram.factory import AdapterType
from ..telegram.factory import factory as adapter_factory
from ..utils import audio_manager as audio_manager_module
from ..utils.i18n import get_tts_commands, t
from ..utils.logging_config import get_logger, setup_logging
from ..utils.parsing import parse_lang_and_text
from ..utils.rate_limiter import check_rate_limit
from .callbacks import CallbackRegistry
from .commands import CommandRegistry

logger = get_logger(__name__)


class UnifiedTTSBot:
    """
    Unified TTS Bot that integrates with any Telegram framework and TTS engine.

    Provides a complete text-to-speech solution for Telegram, supporting multiple
    frameworks (e.g., aiogram, pyrogram) and engines with smart routing and caching.

    Notes:
        Handles message processing, command dispatching, error management, and statistics.
    """

    def __init__(
        self,
        bot_token: str,
        adapter_type: str = "aiogram",
        engine_preferences: dict[str, list[str]] | None = None,
        cache_enabled: bool = True,
        audio_processing: bool = True,
    ):
        """
        Initialize the unified bot.

        Args:
            bot_token: Telegram bot token for authentication.
            adapter_type: Telegram framework to use (e.g., aiogram, pyrogram).
            engine_preferences: Optional engine preferences by language code.
            cache_enabled: Whether to enable audio caching.
            audio_processing: Whether to enable audio processing features.

        Notes:
            Sets up core components like adapter, router, registries, and statistics.
        """
        self.bot_token = bot_token
        self.adapter_type = adapter_type
        self.engine_preferences = engine_preferences or {}
        self.cache_enabled = cache_enabled
        self.audio_processing = audio_processing

        self.adapter: TelegramAdapter | None = None
        self.smart_router: SmartRouter | None = None
        self._running = False
        self._cmd_registry = CommandRegistry()
        self._cb_registry = CallbackRegistry()
        self.sudo_users: set[str] = set(settings.sudo_user_ids)

        self.stats = {
            "messages_processed": 0,
            "synthesis_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "engine_failures": 0,
            "total_processing_time": 0.0,
        }

    def awaitable(self, func):
        """Convert a synchronous function to an awaitable coroutine if needed.

        Args:
            func: The function to wrap.

        Returns:
            A wrapped function that returns an awaitable if the original is sync.
        """

        def call(*args, **kwargs):
            result = func(*args, **kwargs)
            if hasattr(result, "__await__"):
                return result

            class _Awaitable:
                def __await__(self):
                    async def _inner():
                        return result

                    return _inner().__await__()

            return _Awaitable()

        return call

    async def initialize(self) -> None:
        """Initialize bot components including adapter, handlers, engines, and registries.

        Sets up the Telegram adapter, command handlers, TTS engines, and command registry.
        """
        try:
            resolved_adapter = self.adapter_type or settings.telegram_driver
            adapter_type = (
                AdapterType(resolved_adapter)
                if not isinstance(resolved_adapter, AdapterType)
                else resolved_adapter
            )
            self.adapter = adapter_factory.create_adapter(adapter_type, self.bot_token)

            self.adapter.set_message_handler(self._handle_message)
            self.adapter.set_callback_handler(self._handle_callback)
            self.adapter.set_error_handler(self._handle_error)

            if hasattr(engines_factory_module, "setup_registry"):
                engines_factory_module.setup_registry(engines_registry.registry)

            self.smart_router = SmartRouter(engines_registry.registry)

            self._setup_engine_preferences()

            self._cmd_registry.register_default(self)
            self._cb_registry.register_default(self)
            self._cmd_registry.register_admin(self)
            self._cmd_registry.register_advanced_admin(self)

            logger.info("Unified TTS Bot initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    def _setup_engine_preferences(self) -> None:
        """Configure engine preferences for various languages, applying user overrides and defaults.

        Sets up language-specific engine preferences with fallbacks to default engines.
        """
        default_preferences = {
            "fa": ["edge", "piper", "gtts"],
            "en": ["edge", "piper", "gtts"],
            "ar": ["edge", "piper", "gtts"],
            "es": ["edge", "piper", "gtts"],
            "fr": ["edge", "piper", "gtts"],
            "de": ["edge", "piper", "gtts"],
            "it": ["edge", "piper", "gtts"],
            "pt": ["edge", "piper", "gtts"],
            "ru": ["edge", "piper", "gtts"],
            "ja": ["edge", "piper", "gtts"],
            "ko": ["edge", "piper", "gtts"],
            "zh": ["edge", "piper", "gtts"],
        }

        for lang, engines in self.engine_preferences.items():
            engines_registry.registry.set_policy(lang, engines)

        for lang, engines in default_preferences.items():
            if lang not in self.engine_preferences:
                engines_registry.registry.set_policy(lang, engines)

    async def _dispatch_command(self, message: TelegramMessage, text: str) -> bool:
        """Dispatch a registered command and return whether it was handled.

        Args:
            message: The incoming Telegram message.
            text: The text content of the message.

        Returns:
            True if the command was handled successfully.
        """
        return await self._cmd_registry.dispatch(message, text)

    async def start(self) -> None:
        """Start the bot, ensuring initialization and logging setup.

        Initializes the bot if not already done and starts the Telegram adapter.
        """
        try:
            setup_logging(settings.log_level)
            if not self.adapter or not self.smart_router:
                await self.initialize()
            start_method = self.adapter.start
            result = start_method()
            if hasattr(result, "__await__"):
                await result
            self._running = True
            logger.info("Unified TTS Bot started")
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise

    async def stop(self) -> None:
        """Stop the bot gracefully.

        Stops the Telegram adapter and cleans up resources.
        """
        try:
            if self.adapter:
                stop_method = self.adapter.stop
                result = stop_method()
                if hasattr(result, "__await__"):
                    await result
            self._running = False
            logger.info("Unified TTS Bot stopped")
        except Exception as e:
            logger.error(f"Failed to stop bot: {e}")

    async def _handle_message(self, message: TelegramMessage) -> None:
        """Process incoming Telegram messages, handling commands and TTS requests.

        Args:
            message: The incoming Telegram message.

        Notes:
            Updates statistics, checks rate limits, and routes to TTS processing if applicable.
        """
        try:
            self.stats["messages_processed"] += 1

            if message.message_type.value != "text" or not message.text:
                return

            if message.text.strip().startswith("/"):
                if await self._dispatch_command(message, message.text):
                    return

            if not self._is_tts_request(message.text):
                return

            # Debug: Check message.user before using it
            logger.info(f"[UnifiedBot] Message user: {message.user}")
            logger.info(f"[UnifiedBot] Message user type: {type(message.user)}")
            if message.user:
                logger.info(f"[UnifiedBot] Message user id: {message.user.id}")
                logger.info(
                    f"[UnifiedBot] Message user username: {message.user.username}"
                )
            else:
                logger.warning("[UnifiedBot] Message user is None!")

            user_id = str(message.user.id) if message.user else "unknown"
            is_allowed, rate_message = await check_rate_limit(user_id)
            if not is_allowed:
                await self._send_error_message(message.chat_id, rate_message)
                return

            text, lang = self._extract_tts_params(message.text)
            if not text:
                await self._send_error_message(message.chat_id, t("empty_text"))
                return

            await self._process_tts_request(message, text, lang)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._handle_error(e, message)

    async def _handle_callback(self, message: TelegramMessage) -> None:
        """Process callback queries from inline keyboards.

        Args:
            message: The callback query message.

        Notes:
            Dispatches to callback registry; logs unknown callbacks.
        """
        try:
            callback_data = message.text
            if not await self._cb_registry.dispatch(self, message, callback_data):
                logger.debug(f"Unknown callback: {callback_data}")

        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await self._handle_error(e, message)

    async def _handle_error(self, error: Exception, context: Any = None) -> None:
        """Manage errors, log them, update stats, and notify user if possible.

        Args:
            error: The exception that occurred.
            context: Optional context (e.g., message) for user notification.
        """
        logger.error(f"Bot error: {error}")
        self.stats["engine_failures"] += 1

        if context and hasattr(context, "chat_id"):
            await self._send_error_message(context.chat_id, t("general_error"))

    def _is_tts_request(self, text: str) -> bool:
        """Determine if the message text qualifies as a TTS request.

        Args:
            text: The message text to check.

        Returns:
            True if it matches TTS commands or is plain text without slashes.
        """
        tts_commands = get_tts_commands()
        text_lower = text.lower().strip()

        for command in tts_commands:
            if text_lower.startswith(command):
                return True

        if len(text.strip()) > 0 and not text.startswith("/"):
            return True

        return False

    def _extract_tts_params(self, text: str) -> tuple[str, str]:
        """Parse text and language from message, handling commands and brackets.

        Args:
            text: The input message text.

        Returns:
            Tuple of (clean text, language code), defaulting to 'fa' if unspecified.

        Notes:
            Supports bracketed prefixes like [en] and command stripping.
        """
        tts_commands = get_tts_commands()
        payload = text.strip()
        for command in tts_commands:
            if payload.lower().startswith(command):
                payload = payload[len(command) :].strip()
                break
        fallback_lang = "fa"
        if payload.startswith("[") and "]" in payload:
            end = payload.find("]")
            bracket_lang = payload[1:end].strip()
            clean = payload[end + 1 :].strip()
            return clean, (bracket_lang or fallback_lang)

        lang, clean = parse_lang_and_text(payload, fallback_lang)
        return clean, lang

    async def _process_tts_request(
        self, message: TelegramMessage, text: str, lang: str
    ) -> None:
        """Handle TTS synthesis, caching, and sending of audio to the user.

        Args:
            message: The original Telegram message.
            text: The text to synthesize into speech.
            lang: The target language code.

        Notes:
            Checks cache first, synthesizes via smart router if missed, sends voice message,
            and updates statistics. Handles engine failures gracefully.
        """
        try:
            self.stats["synthesis_requests"] += 1
            start_time = asyncio.get_event_loop().time()

            processing_msg = await self.awaitable(self.adapter.send_message)(
                message.chat_id, t("processing")
            )

            try:
                get_audio = audio_manager_module.audio_manager.get_audio
                result = get_audio(text, lang, "smart")
                if hasattr(result, "__await__"):
                    audio_data = await result
                else:
                    audio_data = result
                if audio_data:
                    if self.cache_enabled:
                        self.stats["cache_hits"] += 1
                else:
                    audio_data = None
                    if self.cache_enabled:
                        self.stats["cache_misses"] += 1
            except Exception as err:
                logger.warning("Cache get failed, will synthesize: %s", err)
                audio_data = None
                if self.cache_enabled:
                    self.stats["cache_misses"] += 1

            if audio_data is None:
                try:
                    synth_result = self.smart_router.synth_async(
                        text, lang, requirements={"offline": False}
                    )
                    if hasattr(synth_result, "__await__"):
                        audio_data, engine_name = await synth_result
                    else:
                        audio_data, engine_name = synth_result

                    if self.cache_enabled:
                        try:
                            save_fn = audio_manager_module.audio_manager.get_audio
                            save_res = save_fn(text, lang, "smart")
                            if hasattr(save_res, "__await__"):
                                await save_res
                        except Exception as err:
                            logger.debug("Cache save skipped/failed: %s", err)

                except AllEnginesFailedError:
                    await self.awaitable(self.adapter.send_message)(
                        message.chat_id,
                        t("tts_error"),
                    )
                    return
                except EngineNotFoundError:
                    await self.awaitable(self.adapter.send_message)(
                        message.chat_id, t("engine_not_found", error=lang)
                    )
                    return

            await self.awaitable(self.adapter.send_voice)(
                message.chat_id,
                audio_data,
                caption=t(
                    "voice_caption",
                    text=text[:100] + ("..." if len(text) > 100 else ""),
                ),
                reply_to_message_id=message.id,
            )

            await self.awaitable(self.adapter.delete_message)(
                message.chat_id, processing_msg.id
            )

            processing_time = asyncio.get_event_loop().time() - start_time
            self.stats["total_processing_time"] += processing_time

            logger.info(f"TTS request processed in {processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Error processing TTS request: {e}")
            await self._send_error_message(message.chat_id, t("tts_error"))

    async def _handle_engine_selection(
        self, message: TelegramMessage, callback_data: str
    ) -> None:
        """Update engine policy by prioritizing the selected engine for specified languages.

        Args:
            message: The callback message.
            callback_data: Data containing engine token and optional language.

        Notes:
            Targets default languages if none specified; confirms change to user.
        """
        try:
            parts = callback_data.split(":", 1)
            engine_token = parts[0]
            forced_lang = parts[1] if len(parts) > 1 and parts[1] else None
            if not engine_token.startswith("engine_"):
                return
            selected_engine = engine_token.replace("engine_", "").strip()

            target_langs = [forced_lang] if forced_lang else ["fa", "en", "ar"]
            for lang in target_langs:
                current = engines_registry.registry.get_policy(lang)
                if not current:
                    current = engines_registry.registry.get_available_engines()
                new_order = [selected_engine] + [
                    e for e in current if e != selected_engine
                ]
                engines_registry.registry.set_policy(lang, new_order)

            await self.awaitable(self.adapter.send_message)(
                message.chat_id, t("engine_priority_set", engine=selected_engine)
            )
        except Exception as e:
            await self.awaitable(self.adapter.send_message)(
                message.chat_id, t("engine_change_error", error=e)
            )

    async def _handle_settings_callback(
        self, message: TelegramMessage, callback_data: str
    ) -> None:
        """Toggle cache or audio processing settings based on callback data.

        Args:
            message: The callback message.
            callback_data: Identifier for the setting (e.g., 'settings_cache_on').

        Notes:
            Updates instance flags and sends confirmation message.
        """
        try:
            if callback_data == "settings_cache_on":
                self.cache_enabled = True
                text = t("cache_enabled")
            elif callback_data == "settings_cache_off":
                self.cache_enabled = False
                text = t("cache_disabled")
            elif callback_data == "settings_audio_on":
                self.audio_processing = True
                text = t("audio_enabled")
            elif callback_data == "settings_audio_off":
                self.audio_processing = False
                text = t("audio_disabled")
            else:
                text = t("unknown_setting")

            await self.awaitable(self.adapter.send_message)(message.chat_id, text)
        except Exception as e:
            await self.awaitable(self.adapter.send_message)(
                message.chat_id, t("settings_change_error", error=e)
            )

    async def _send_error_message(self, chat_id: int, error_text: str) -> None:
        """Send an error notification to the specified chat.

        Args:
            chat_id: The target chat ID.
            error_text: The error message content.

        Notes:
            Prepends an emoji for visibility; logs failures.
        """
        try:
            await self.awaitable(self.adapter.send_message)(chat_id, f"❌ {error_text}")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Retrieve comprehensive bot statistics including engines and cache.

        Returns:
            Dictionary with processing stats, engine info, cache metrics, and averages.

        Notes:
            Calculates average processing time and cache hit rate on the fly.
        """
        stats = self.stats.copy()

        if self.smart_router:
            stats["engine_stats"] = self.smart_router.get_all_stats()

        if self.cache_enabled:
            stats["cache_stats"] = audio_manager_module.audio_manager.get_cache_stats()

        if stats["synthesis_requests"] > 0:
            stats["avg_processing_time"] = (
                stats["total_processing_time"] / stats["synthesis_requests"]
            )
        else:
            stats["avg_processing_time"] = 0.0

        if stats["synthesis_requests"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["synthesis_requests"]
        else:
            stats["cache_hit_rate"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """Clear all bot statistics to zero."""
        self.stats = {
            "messages_processed": 0,
            "synthesis_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "engine_failures": 0,
            "total_processing_time": 0.0,
        }

        if self.smart_router:
            self.smart_router.reset_stats()

    async def get_engine_info(self) -> dict[str, Any]:
        """Fetch details on available TTS engines, capabilities, stats, and rankings.

        Returns:
            Dictionary with available engines, capabilities, stats, and language-specific rankings.
        """
        if not self.smart_router:
            return {}

        return {
            "available_engines": engines_registry.registry.get_available_engines(),
            "engine_capabilities": engines_registry.registry.get_capabilities_summary(),
            "engine_stats": self.smart_router.get_all_stats(),
            "engine_rankings": {
                lang: self.smart_router.get_engine_ranking(lang)
                for lang in [
                    "fa",
                    "en",
                    "ar",
                    "es",
                    "fr",
                    "de",
                    "it",
                    "pt",
                    "ru",
                    "ja",
                    "ko",
                    "zh",
                ]
            },
        }

    @property
    def is_running(self) -> bool:
        """Indicate whether the bot is currently active.

        Returns:
            True if the bot is running.
        """
        return self._running

    def is_sudo(self, user_id: int | str) -> bool:
        """Verify if a user has admin (sudo) privileges.

        Args:
            user_id: The user ID to check (int or str).

        Returns:
            True if the user is in the sudo list.
        """
        try:
            user_id_str = str(user_id)
        except Exception:
            return False
        return user_id_str in (self.sudo_users or settings.sudo_user_ids)
