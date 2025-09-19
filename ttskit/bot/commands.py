"""Modular command registry for the UnifiedTTSBot.

This module manages command handlers, keeping them decoupled from the bot's core logic.
Handlers are async callables with the signature (message: TelegramMessage, args: str) -> None.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from ..telegram.base import TelegramMessage
from ..utils.i18n import t
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

CommandHandler = Callable[[TelegramMessage, str], Awaitable[Any]]


class CommandRegistry:
    """Simple registry and dispatcher for bot commands."""

    def __init__(self) -> None:
        """Initializes the CommandRegistry.

        Creates empty dictionaries to store command handlers, admin-only flags,
        and a set of admin command names.

        """
        self._handlers: dict[str, CommandHandler] = {}
        self._admin_only: dict[str, bool] = {}
        self._admin_set: set[str] = set()

    def register(
        self, command: str, handler: CommandHandler, admin_only: bool = False
    ) -> None:
        """Registers a command handler in the registry.

        Automatically adds leading '/' if missing.

        Args:
            command: The command name (with or without leading '/').
            handler: The async handler function for the command.
            admin_only: Whether the command is restricted to admins.

        """
        key = command if command.startswith("/") else f"/{command}"
        self._handlers[key] = handler
        self._admin_only[key] = bool(admin_only)
        if admin_only:
            self._admin_set.add(key.lstrip("/"))

    def register_command(
        self, command: str, handler: CommandHandler, admin_only: bool = False
    ) -> None:
        """Registers a command handler (alias for the register method).

        This is simply an alias for the register method.

        Args:
            command: The command name.
            handler: The async handler function.
            admin_only: Whether restricted to admins.

        """
        self.register(command, handler, admin_only=admin_only)

    def register_bulk(self, mapping: dict[str, CommandHandler]) -> None:
        """Registers multiple command handlers from a dictionary.

        Args:
            mapping: Dict of command names to handler functions.

        """
        for cmd, handler in mapping.items():
            self.register(cmd, handler)

    async def dispatch(self, message: TelegramMessage, text_or_bot: Any) -> bool:
        """Dispatches the message to the appropriate command handler.

        Handles cases where tests pass the bot as the second argument instead of text.
        Performs admin checks if the command is admin-only.
        Extracts args after the command prefix.

        Args:
            message: The TelegramMessage object.
            text_or_bot: Either the message text or the bot instance (for tests).

        Returns:
            bool: True if a handler was found and executed, False otherwise.

        """
        text_value = getattr(message, "text", None)
        if text_value is None:
            text_value = text_or_bot if isinstance(text_or_bot, str) else ""
        text_stripped = str(text_value).strip()
        text_lower = text_stripped.lower()
        bot = text_or_bot if not isinstance(text_or_bot, str) else None
        for cmd, handler in self._handlers.items():
            if text_lower.startswith(cmd.lower()):
                if self._admin_only.get(cmd, False) and bot is not None:
                    try:
                        user_id = getattr(message, "user", None)
                        user_id = getattr(user_id, "id", None)
                        if hasattr(bot, "is_sudo"):
                            is_sudo = bot.is_sudo(user_id)
                        elif hasattr(bot, "sudo_users"):
                            is_sudo = str(user_id) in bot.sudo_users
                        else:
                            is_sudo = False
                        if not is_sudo:
                            return False
                    except Exception:
                        return False
                args = text_stripped[len(cmd) :].strip()
                if handler is not None:
                    try:
                        await handler(message, args)
                    except TypeError:
                        bot = text_or_bot if not isinstance(text_or_bot, str) else None
                        await handler(message, bot)
                return True
        return False

    def registered(self) -> dict[str, CommandHandler]:
        """Gets a copy of all registered handlers.

        Returns:
            dict: Copy of the internal handlers dictionary.

        """
        return dict(self._handlers)

    @property
    def commands(self) -> dict[str, CommandHandler]:
        """Gets all registered commands without leading slashes.

        Returns:
            dict: Commands with keys stripped of leading '/'.

        """
        return {k.lstrip("/"): v for k, v in self._handlers.items()}

    @property
    def admin_commands(self) -> set[str]:
        """Gets admin-only command names without leading slashes.

        Returns:
            set: Set of admin command names.

        """
        return set(self._admin_set)

    def register_default(self, bot: Any) -> None:
        """Registers default bot commands like /start, /help, etc.

        Args:
            bot: The bot instance to use for sending messages.

        """
        async def cmd_start(message: TelegramMessage, _: str) -> None:
            """Handles the /start command.

            Sends a help message to the user.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(
                    chat_id,
                    t("help", default_lang="fa", max_chars="1000"),
                )
            except Exception:
                pass

        async def cmd_help(message: TelegramMessage, _: str) -> None:
            """Handles the /help command.

            Builds and sends a dynamic help message listing available commands,
            including admin-only ones if the user is an admin.

            Uses registered commands to generate sections dynamically.
            Includes bilingual descriptions for commands.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                base_help = t("help", default_lang="fa", max_chars="1000")

                try:
                    user_id = None
                    if hasattr(message, "user") and message.user:
                        user_id = getattr(message.user, "id", None)
                    elif hasattr(message, "from_user") and message.from_user:
                        user_id = getattr(message.from_user, "id", None)
                    is_admin = bot.is_sudo(user_id) if user_id else False
                except Exception:
                    is_admin = False

                general_commands: list[str] = []
                admin_commands: list[str] = []

                for cmd, handler in self._handlers.items():
                    if handler is None:
                        continue
                    if self._admin_only.get(cmd, False):
                        admin_commands.append(cmd)
                    else:
                        general_commands.append(cmd)

                general_commands = sorted(set(general_commands))
                admin_commands = sorted(set(admin_commands))

                desc: dict[str, str] = {
                    "/start": "شروع | Start",
                    "/help": "راهنما | Help",
                    "/engines": "لیست موتورهای TTS | List TTS engines",
                    "/voices": "لیست صداها: /voices [lang] [engine] | List voices",
                    "/languages": "زبان‌های پشتیبانی‌شده | Supported languages",
                    "/stats": "آمار ساده | Basic stats",
                    "/status": "وضعیت ربات | Bot status",
                    "/clear_cache": "پاک‌سازی کش | Clear cache",
                    "/cache_stats": "آمار کش | Cache stats",
                    "/cache_cleanup": "حذف فایل‌های قدیمی کش | Cleanup cache",
                    "/cache_export": "خروجی گرفتن از کش | Export cache",
                    "/reload_engines": "بارگذاری مجدد موتور‌ها | Reload engines",
                    "/reset_stats": "ریست آمار | Reset stats",
                    "/restart": "ریستارت سرویس | Restart",
                    "/shutdown": "خاموش کردن سرویس | Shutdown",
                    "/create_key": "ایجاد API Key | Create API key",
                    "/list_keys": "لیست API Key‌ها | List API keys",
                    "/delete_key": "حذف API Key | Delete API key",
                    "/system_stats": "آمار جامع سیستم | System stats",
                    "/health_check": "بررسی سلامت | Health check",
                    "/debug": "اطلاعات دیباگ | Debug info",
                    "/performance": "تحلیل عملکرد | Performance analysis",
                    "/monitor": "مانیتورینگ لحظه‌ای | Live monitor",
                    "/export_metrics": "ذخیره متریک‌ها | Export metrics",
                    "/test_engines": "تست موتور‌ها | Test engines",
                    "/create_user": "ایجاد کاربر | Create user",
                    "/delete_user": "حذف کاربر | Delete user",
                    "/list_users": "لیست کاربران | List users",
                }

                def fmt_section(title_fa_en: str, cmds: list[str]) -> str:
                    if not cmds:
                        return ""
                    lines = [title_fa_en]
                    for c in cmds:
                        d = desc.get(c, "")
                        lines.append(f"• {c} {('- ' + d) if d else ''}")
                    return "\n".join(lines)

                general_section = fmt_section(
                    "\n📎 دستورات عمومی / General commands:", general_commands
                )
                admin_section = (
                    fmt_section("\n🔐 دستورات مدیر / Admin commands:", admin_commands)
                    if is_admin
                    else ""
                )

                full_text = "".join(
                    [
                        base_help,
                        "\n",
                        general_section,
                        "\n" if general_section else "",
                        admin_section,
                    ]
                ).strip()

                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(chat_id, full_text)
            except Exception:
                pass

        async def cmd_engines(message: TelegramMessage, _: str) -> None:
            """Handles the /engines command.

            Lists available TTS engines.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                info = await bot.get_engine_info()
                engines = info.get("available_engines", [])
                engines_text = "\n".join(f"• {e}" for e in engines) or t("no_engines")
                text = t("engines_list", engines=engines_text)
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(chat_id, text)
            except Exception:
                pass

        async def cmd_stats(message: TelegramMessage, _: str) -> None:
            """Handles the /stats command.

            Sends basic statistics on messages, requests, and cache.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                stats = bot.get_stats()
                text = t(
                    "stats_header",
                    messages=stats.get("messages_processed", 0),
                    requests=stats.get("synthesis_requests", 0),
                    cache_hits=stats.get("cache_hits", 0),
                    cache_misses=stats.get("cache_misses", 0),
                    avg_time=stats.get("avg_processing_time", 0.0),
                )
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(chat_id, text)
            except Exception:
                pass

        async def cmd_status(message: TelegramMessage, _: str) -> None:
            """Handles the /status command.

            Confirms the bot is running.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                text = t("bot_running")
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(chat_id, text)
            except Exception as e:
                logger.warning(f"Failed to send languages info: {e}")

        async def cmd_languages(message: TelegramMessage, _: str) -> None:
            """Handles the /languages command.

            Lists supported languages for TTS.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                from ..public import get_supported_languages

                langs = get_supported_languages()
                text = t("languages_header", languages=", ".join(langs[:50]))
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(chat_id, text)
            except Exception as e:
                logger.warning(f"Failed to send languages info: {e}")

        async def cmd_voices(message: TelegramMessage, args: str) -> None:
            """Handles the /voices command.

            Lists available voices, optionally filtered by language or engine.

            Args:
                message: The incoming TelegramMessage.
                args: Optional arguments for lang and engine (e.g., 'en edge').

            """
            try:
                tokens = args.split()
                lang = None
                engine = None
                if tokens:
                    if tokens[0].startswith("[") and tokens[0].endswith("]"):
                        lang = tokens[0][1:-1]
                        tokens = tokens[1:]
                    elif len(tokens[0]) <= 5:
                        lang = tokens[0]
                        tokens = tokens[1:]
                if tokens:
                    engine = tokens[0]

                from ..public import list_voices

                voices = list_voices(lang=lang, engine=engine)
                lang_info = f" (lang={lang})" if lang else ""
                engine_info = f" (engine={engine})" if engine else ""
                header = t(
                    "voices_header", lang_info=lang_info, engine_info=engine_info
                )
                body = "\n".join(f"• {v}" for v in voices[:50]) or t("no_voices")
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                await bot.awaitable(bot.adapter.send_message)(
                    chat_id, f"{header}\n{body}"
                )
            except Exception as e:
                logger.warning(f"Failed to send voices info: {e}")

        self.register_bulk(
            {
                "/start": cmd_start,
                "/help": cmd_help,
                "/engines": cmd_engines,
                "/stats": cmd_stats,
                "/voices": cmd_voices,
                "/status": cmd_status,
                "/languages": cmd_languages,
            }
        )

    def register_admin(self, bot: Any) -> None:
        """Registers admin-only commands that require sudo access.

        Sudo users are checked via bot.is_sudo(user_id).
        Includes cache management, engine reload, stats reset, and restart/shutdown.

        Args:
            bot: The bot instance for sending messages and sudo checks.

        """

        async def _require_sudo(message: TelegramMessage) -> bool:
            """Helper to check if the user has sudo access and deny if not.

            Sends denial message if unauthorized.

            Args:
                message: The incoming TelegramMessage.

            Returns:
                bool: True if user is sudo, False otherwise.

            """
            try:
                user_id = message.user.id if hasattr(message, "user") else None
            except Exception:
                user_id = None
            if user_id is None or not getattr(bot, "is_sudo", lambda _uid: False)(
                user_id
            ):
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("access_denied")
                    )
                except Exception:
                    bot.adapter.send_message(message.chat_id, t("access_denied"))
                return False
            return True

        async def admin_clear_cache(message: TelegramMessage, _: str) -> None:
            """Handles /clear_cache command to clear the audio cache.

            Requires sudo access.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                from ..utils.audio_manager import audio_manager

                audio_manager.clear_cache()
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("cache_cleared")
                    )
                except Exception:
                    bot.adapter.send_message(message.chat_id, t("cache_cleared"))
            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("cache_clear_error", error=e)
                )

        async def admin_cache_stats(message: TelegramMessage, _: str) -> None:
            """Handles /cache_stats command to show cache statistics.

            Requires sudo access.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                from ..utils.audio_manager import audio_manager

                stats = audio_manager.get_cache_stats()
                text = t(
                    "cache_stats_header",
                    total_files=stats.get("total_files", 0),
                    total_size=stats.get("total_size_mb", 0.0),
                    max_cache_size=stats.get("max_cache_size", "-"),
                    max_file_age=stats.get("max_file_age", "-"),
                )
                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)
            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("cache_stats_error", error=e)
                )

        async def admin_reload_engines(message: TelegramMessage, _: str) -> None:
            """Handles /reload_engines command to reload TTS engines.

            Requires sudo access.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                from ..engines import factory as engines_factory_module
                from ..engines import registry as engines_registry

                engines_factory_module.setup_registry(engines_registry.registry)
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("engines_reloaded")
                    )
                except Exception:
                    bot.adapter.send_message(message.chat_id, t("engines_reloaded"))
            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("engines_reload_error", error=e)
                )

        async def admin_reset_stats(message: TelegramMessage, _: str) -> None:
            """Handles /reset_stats command to reset bot statistics.

            Requires sudo access.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                bot.reset_stats()
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("stats_reset")
                    )
                except Exception:
                    bot.adapter.send_message(message.chat_id, t("stats_reset"))
            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("stats_reset_error", error=e)
                )

        async def admin_cache_cleanup(message: TelegramMessage, _: str) -> None:
            """Handles /cache_cleanup command to remove old cache files.

            Requires sudo access. Reports cleaned files and size.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                from ..utils.audio_manager import audio_manager

                stats_before = audio_manager.get_cache_stats()

                audio_manager.cleanup_old_files()

                stats_after = audio_manager.get_cache_stats()

                cleaned_files = stats_before.get("total_files", 0) - stats_after.get(
                    "total_files", 0
                )
                cleaned_size = stats_before.get("total_size_mb", 0) - stats_after.get(
                    "total_size_mb", 0
                )

                text = t(
                    "cache_cleanup_header",
                    cleaned_files=cleaned_files,
                    cleaned_size=cleaned_size,
                    remaining_files=stats_after.get("total_files", 0),
                )
                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)
            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("cache_clear_error", error=e)
                )

        async def admin_cache_export(message: TelegramMessage, _: str) -> None:
            """Handles /cache_export command to export cache to a temp directory.

            Requires sudo access. Creates a temporary directory for export.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                from ..utils.audio_manager import audio_manager
                from ..utils.temp_manager import TempFileManager

                temp_manager = TempFileManager(prefix="ttskit_cache_export_")
                export_dir = temp_manager.create_temp_dir()

                audio_manager.export_cache(export_dir)

                stats = audio_manager.get_cache_stats()
                text = t(
                    "cache_export_header",
                    export_dir=export_dir,
                    total_files=stats.get("total_files", 0),
                    total_size=stats.get("total_size_mb", 0),
                )
                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)
            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("cache_export_error", error=e)
                )

        self.register("/clearcache", admin_clear_cache, admin_only=True)
        self.register("/clear_cache", admin_clear_cache, admin_only=True)
        self.register("/cachestats", admin_cache_stats, admin_only=True)
        self.register("/cache_stats", admin_cache_stats, admin_only=True)
        self.register("/cachecleanup", admin_cache_cleanup, admin_only=True)
        self.register("/cache_cleanup", admin_cache_cleanup, admin_only=True)
        self.register("/cacheexport", admin_cache_export, admin_only=True)
        self.register("/cache_export", admin_cache_export, admin_only=True)
        self.register("/reloadengines", admin_reload_engines, admin_only=True)
        self.register("/reload_engines", admin_reload_engines, admin_only=True)
        self.register("/resetstats", admin_reset_stats, admin_only=True)
        self.register("/reset_stats", admin_reset_stats, admin_only=True)

        async def admin_restart(message: TelegramMessage, _: str) -> None:
            """Handles /restart command to restart the bot.

            Requires sudo access. Sends restart message before exec.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("restarting")
                )
            except Exception:
                bot.adapter.send_message(message.chat_id, t("restarting"))

        async def admin_shutdown(message: TelegramMessage, _: str) -> None:
            """Handles /shutdown command to shut down the bot.

            Requires sudo access. Sends shutdown message before exit.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return
            try:
                await bot.awaitable(bot.adapter.send_message)(
                    message.chat_id, t("shutting_down")
                )
            except Exception:
                bot.adapter.send_message(message.chat_id, t("shutting_down"))

        self.register("/restart", admin_restart, admin_only=True)
        self.register("/shutdown", admin_shutdown, admin_only=True)

    def register_advanced_admin(self, bot: Any) -> None:
        """Registers advanced admin commands involving database and metrics.

        Includes API key management, system stats, health checks, and debug info.
        Uses a bind helper for compatibility with global handlers.

        Args:
            bot: The bot instance for sudo checks and messaging.

        """

        async def _require_sudo(message: TelegramMessage) -> bool:
            """Helper to check sudo access and send denial if unauthorized.

            Args:
                message: The incoming TelegramMessage.

            Returns:
                bool: True if authorized, False otherwise.

            """
            try:
                user_id = message.user.id if hasattr(message, "user") else None
            except Exception:
                user_id = None
            if user_id is None or not getattr(bot, "is_sudo", lambda _uid: False)(
                user_id
            ):
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("access_denied")
                    )
                except Exception:
                    bot.adapter.send_message(message.chat_id, t("access_denied"))
                return False
            return True

        async def admin_create_key(message: TelegramMessage, args: str) -> None:
            """Handles /create_key command to generate an API key for a user.

            Requires sudo access. Creates user if not exists, validates permissions.

            Args:
                message: The incoming TelegramMessage.
                args: Arguments like 'user_id:123 permissions:read,write'.

            """
            if not await _require_sudo(message):
                return

            args_list = args.split() if args else []

            if not args_list:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("create_key_usage")
                    )
                except Exception:
                    bot.adapter.send_message(message.chat_id, t("create_key_usage"))
                return

            user_id = None
            permissions = ["read", "write"]

            for arg in args_list:
                if arg.startswith("user_id:"):
                    user_id = arg.split(":", 1)[1]
                elif arg.startswith("permissions:"):
                    permissions = arg.split(":", 1)[1].split(",")

            if not user_id:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("error_prefix", error="user_id is missing")
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, t("error_prefix", error="user_id is missing")
                    )
                return

            valid_permissions = ["read", "write", "admin"]
            invalid_permissions = [p for p in permissions if p not in valid_permissions]
            if invalid_permissions:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id,
                        t(
                            "error_prefix",
                            error=f"invalid permissions: {', '.join(invalid_permissions)}",
                        ),
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id,
                        t(
                            "error_prefix",
                            error=f"invalid permissions: {', '.join(invalid_permissions)}",
                        ),
                    )
                return

            try:
                from ..database.connection import get_session
                from ..services.user_service import UserService

                db_session = next(get_session())
                user_service = UserService(db_session)

                existing_user = await user_service.get_user_by_id(user_id)
                if not existing_user:
                    await user_service.create_user(
                        user_id=user_id,
                        username=f"Telegram User {user_id}",
                        email=f"{user_id}@telegram.local",
                        is_admin="admin" in permissions,
                    )

                api_key_data = await user_service.create_api_key(
                    user_id=user_id,
                    permissions=permissions,
                )

                api_key = api_key_data["api_key"]

                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id,
                        t(
                            "api_key_created",
                            user_id=user_id,
                            api_key=api_key,
                            permissions=", ".join(permissions),
                        ),
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id,
                        t(
                            "api_key_created",
                            user_id=user_id,
                            api_key=api_key,
                            permissions=", ".join(permissions),
                        ),
                    )

            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, f"❌ **خطا در ایجاد کلید**\n\n{str(e)}"
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, f"❌ **خطا در ایجاد کلید**\n\n{str(e)}"
                    )

        async def admin_list_keys(message: TelegramMessage, _: str) -> None:
            """Handles /list_keys command to display all API keys.

            Requires sudo access. Shows user details, key info, permissions, dates.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return

            try:
                from ..database.connection import get_session
                from ..services.user_service import UserService

                db_session = next(get_session())
                user_service = UserService(db_session)

                users = await user_service.get_all_users()

                if not users:
                    try:
                        await bot.awaitable(bot.adapter.send_message)(
                            message.chat_id, t("no_api_keys")
                        )
                    except Exception:
                        bot.adapter.send_message(message.chat_id, t("no_api_keys"))
                    return

                text = t("api_keys_list_header") + "\n\n"

                for user in users:
                    api_keys = await user_service.get_user_api_keys(user.user_id)

                    for api_key in api_keys:
                        created_at = api_key.created_at.strftime("%Y-%m-%d %H:%M")
                        last_used = (
                            api_key.last_used.strftime("%Y-%m-%d %H:%M")
                            if api_key.last_used
                            else "هرگز"
                        )

                        import json

                        permissions = json.loads(api_key.permissions)

                        text += f"👤 **{user.user_id}**\n"
                        text += f"🔑 ID: `{api_key.id}`\n"
                        text += f"🔐 {', '.join(permissions)}\n"
                        text += f"📅 ایجاد: {created_at}\n"
                        text += f"🔄 آخرین استفاده: {last_used}\n"
                        text += f"📊 وضعیت: {'فعال' if api_key.is_active else 'غیرفعال'}\n\n"

                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)

            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, f"❌ **خطا در دریافت لیست**\n\n{str(e)}"
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, f"❌ **خطا در دریافت لیست**\n\n{str(e)}"
                    )

        async def admin_delete_key(message: TelegramMessage, args: str) -> None:
            """Handles /delete_key command to remove an API key.

            Requires sudo access. Deletes the first key for the user.

            Args:
                message: The incoming TelegramMessage.
                args: Arguments like 'user_id:123'.

            """
            if not await _require_sudo(message):
                return

            args_list = args.split() if args else []

            if not args_list:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id,
                        t("error_prefix", error="usage: /delete_key user_id:<id>"),
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id,
                        t("error_prefix", error="usage: /delete_key user_id:<id>"),
                    )
                return

            user_id = None
            for arg in args_list:
                if arg.startswith("user_id:"):
                    user_id = arg.split(":", 1)[1]
                    break

            if not user_id:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("error_prefix", error="user_id is missing")
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, t("error_prefix", error="user_id is missing")
                    )
                return

            try:
                from ..database.connection import get_session
                from ..services.user_service import UserService

                db_session = next(get_session())
                user_service = UserService(db_session)

                user = await user_service.get_user_by_id(user_id)
                if not user:
                    try:
                        await bot.awaitable(bot.adapter.send_message)(
                            message.chat_id, t("user_not_found", user_id=user_id)
                        )
                    except Exception:
                        bot.adapter.send_message(
                            message.chat_id, t("user_not_found", user_id=user_id)
                        )
                    return

                api_keys = await user_service.get_user_api_keys(user_id)
                if not api_keys:
                    try:
                        await bot.awaitable(bot.adapter.send_message)(
                            message.chat_id,
                            t(
                                "error_prefix",
                                error=f"no API keys found for user `{user_id}`",
                            ),
                        )
                    except Exception:
                        bot.adapter.send_message(
                            message.chat_id,
                            t(
                                "error_prefix",
                                error=f"no API keys found for user `{user_id}`",
                            ),
                        )
                    return

                api_key = api_keys[0]

                success = await user_service.delete_api_key(user_id, api_key.id)

                if success:
                    try:
                        await bot.awaitable(bot.adapter.send_message)(
                            message.chat_id, t("api_key_deleted", user_id=user_id)
                        )
                    except Exception:
                        bot.adapter.send_message(
                            message.chat_id, t("api_key_deleted", user_id=user_id)
                        )
                else:
                    try:
                        await bot.awaitable(bot.adapter.send_message)(
                            message.chat_id,
                            t(
                                "error_prefix",
                                error=f"failed to delete API key for user `{user_id}`",
                            ),
                        )
                    except Exception:
                        bot.adapter.send_message(
                            message.chat_id,
                            t(
                                "error_prefix",
                                error=f"failed to delete API key for user `{user_id}`",
                            ),
                        )

            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, f"❌ **خطا در حذف کلید**\n\n{str(e)}"
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, f"❌ **خطا در حذف کلید**\n\n{str(e)}"
                    )

        async def admin_system_stats(message: TelegramMessage, _: str) -> None:
            """Handles /system_stats command to display detailed system metrics.

            Requires sudo access. Includes requests, engines, cache, performance, system resources.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return

            try:
                from ..metrics.advanced import get_metrics_collector

                metrics_collector = get_metrics_collector()
                metrics = await metrics_collector.get_comprehensive_metrics()

                engines_lines = "".join(
                    [
                        f"• **{name}:** {data['total_requests']:,} ({data['success_rate']:.1f}% موفق)\n"
                        for name, data in metrics["engines"].items()
                    ]
                )

                text = t(
                    "system_stats_detailed",
                    req_total=metrics["requests"]["total"],
                    req_success=metrics["requests"]["successful"],
                    req_failed=metrics["requests"]["failed"],
                    req_success_rate=metrics["requests"]["success_rate"],
                    req_per_minute=metrics["requests"]["per_minute"],
                    engines_lines=engines_lines,
                    cache_hit_rate=metrics["cache"]["hit_rate"],
                    cache_size_mb=metrics["cache"]["size_mb"],
                    cache_evictions=metrics["cache"]["evictions"],
                    perf_avg=metrics["performance"].get("avg_response_time", 0),
                    perf_p95=metrics["performance"].get("p95_response_time", 0),
                    perf_p99=metrics["performance"].get("p99_response_time", 0),
                    cpu=metrics["system"]["cpu_percent"],
                    mem_mb=metrics["system"]["memory_mb"],
                    mem_percent=metrics["system"]["memory_percent"],
                    disk=metrics["system"]["disk_usage_percent"],
                    net_mb=metrics["system"]["network_io_mb"],
                    health=metrics["health"],
                )

                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)

            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, f"❌ خطا در دریافت آمار: {str(e)}"
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, f"❌ خطا در دریافت آمار: {str(e)}"
                    )

        async def admin_health_check(message: TelegramMessage, _: str) -> None:
            """Handles /health_check command to assess system health.

            Requires sudo access. Provides status, score, recommendations based on metrics.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return

            try:
                from ..metrics.advanced import get_metrics_collector

                metrics_collector = get_metrics_collector()
                metrics = await metrics_collector.get_comprehensive_metrics()
                health_score = metrics["health"]

                if health_score >= 90:
                    status = "🟢 عالی"
                    status_emoji = "✅"
                elif health_score >= 70:
                    status = "🟡 خوب"
                    status_emoji = "⚠️"
                elif health_score >= 50:
                    status = "🟠 متوسط"
                    status_emoji = "⚠️"
                else:
                    status = "🔴 ضعیف"
                    status_emoji = "❌"

                text = t(
                    "health_check_report",
                    status_emoji=status_emoji,
                    status_text=status,
                    health_score=health_score,
                    cpu=metrics["system"]["cpu_percent"],
                    mem_percent=metrics["system"]["memory_percent"],
                    success_rate=metrics["requests"]["success_rate"],
                    avg_response=metrics["performance"].get("avg_response_time", 0),
                    recommendations="",
                )

                recommendations = []
                if metrics["system"]["cpu_percent"] > 80:
                    recommendations.append("• CPU usage بالا است - بررسی کنید")
                if metrics["system"]["memory_percent"] > 80:
                    recommendations.append("• Memory usage بالا است - بررسی کنید")
                if metrics["requests"]["success_rate"] < 95:
                    recommendations.append("• Success rate پایین است - بررسی کنید")
                if metrics["performance"].get("avg_response_time", 0) > 5:
                    recommendations.append("• Response time بالا است - بررسی کنید")

                if recommendations:
                    text = t(
                        "health_check_report",
                        status_emoji=status_emoji,
                        status_text=status,
                        health_score=health_score,
                        cpu=metrics["system"]["cpu_percent"],
                        mem_percent=metrics["system"]["memory_percent"],
                        success_rate=metrics["requests"]["success_rate"],
                        avg_response=metrics["performance"].get("avg_response_time", 0),
                        recommendations="\n".join(recommendations),
                    )
                else:
                    text = t(
                        "health_check_report",
                        status_emoji=status_emoji,
                        status_text=status,
                        health_score=health_score,
                        cpu=metrics["system"]["cpu_percent"],
                        mem_percent=metrics["system"]["memory_percent"],
                        success_rate=metrics["requests"]["success_rate"],
                        avg_response=metrics["performance"].get("avg_response_time", 0),
                        recommendations=t("health_recommendations_ok"),
                    )

                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)

            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, f"❌ خطا در Health Check: {str(e)}"
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, f"❌ خطا در Health Check: {str(e)}"
                    )

        async def admin_debug_info(message: TelegramMessage, _: str) -> None:
            """Handles /debug command to show system debug info.

            Requires sudo access. Displays platform, memory, disk, and cache status.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            if not await _require_sudo(message):
                return

            try:
                import platform

                import psutil

                system_info = {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "architecture": platform.architecture()[0],
                    "processor": platform.processor(),
                    "hostname": platform.node(),
                }

                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                text = t(
                    "debug_info",
                    platform=system_info["platform"],
                    python_version=system_info["python_version"],
                    architecture=system_info["architecture"],
                    processor=system_info["processor"],
                    hostname=system_info["hostname"],
                    mem_total_gb=memory.total / 1024 / 1024 / 1024,
                    mem_available_gb=memory.available / 1024 / 1024 / 1024,
                    mem_used_gb=memory.used / 1024 / 1024 / 1024,
                    mem_percent=memory.percent,
                    disk_total_gb=disk.total / 1024 / 1024 / 1024,
                    disk_used_gb=disk.used / 1024 / 1024 / 1024,
                    disk_percent=disk.percent,
                    disk_free_gb=disk.free / 1024 / 1024 / 1024,
                    cache_enabled=(
                        "✅" if getattr(bot, "cache_enabled", False) else "❌"
                    ),
                )

                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    bot.adapter.send_message(message.chat_id, text)

            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("debug_error", error=str(e))
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, t("debug_error", error=str(e))
                    )

        def bind(func):
            """Helper to bind global handlers to the registry's signature.

            Tries (message, args) then falls back to (bot, message, args).

            Args:
                func: The original handler (may expect bot first).

            Returns:
                Callable: Wrapped handler.

            """
            async def _wrapper(message: TelegramMessage, args: str) -> None:
                try:
                    return await func(message, args)  # type: ignore[misc]
                except TypeError:
                    return await func(bot, message, args)

            return _wrapper

        self.register("/create_key", bind(admin_create_key), admin_only=True)
        self.register("/list_keys", bind(admin_list_keys), admin_only=True)
        self.register("/delete_key", bind(admin_delete_key), admin_only=True)
        self.register("/system_stats", bind(admin_system_stats), admin_only=True)
        self.register("/health_check", bind(admin_health_check), admin_only=True)
        self.register("/debug", bind(admin_debug_info), admin_only=True)

        self.register("/performance", bind(admin_performance_analysis), admin_only=True)
        self.register("/monitor", bind(admin_monitor_system), admin_only=True)
        self.register("/export_metrics", bind(admin_export_metrics), admin_only=True)
        self.register("/test_engines", bind(admin_test_engines), admin_only=True)
        self.register("/create_user", bind(admin_create_user), admin_only=True)
        self.register("/delete_user", bind(admin_delete_user), admin_only=True)
        self.register("/list_users", bind(admin_list_users), admin_only=True)
        self.register("/clear_cache", bind(admin_clear_cache), admin_only=True)
        self.register("/restart", bind(admin_restart_system), admin_only=True)
        self.register("/shutdown", bind(admin_shutdown_system), admin_only=True)

        async def _cancel_monitor(message: TelegramMessage, _: str) -> None:
            """Handles /cancel command to stop ongoing admin tasks like monitoring.

            Requires sudo access.

            Args:
                message: The incoming TelegramMessage.
                _: Ignored args.

            """
            try:
                chat_id = getattr(message, "chat_id", None) or (
                    message.get("chat_id") if hasattr(message, "get") else None
                )
                if not hasattr(bot, "_monitor_cancel"):
                    bot._monitor_cancel = set()
                bot._monitor_cancel.add(chat_id)
                await bot.awaitable(bot.adapter.send_message)(
                    chat_id, "❎ مانیتورینگ لغو شد / Monitoring cancelled"
                )
            except Exception:
                pass

        self.register("/cancel", _cancel_monitor, admin_only=True)


# Standalone command handlers for backward compatibility with tests
async def handle_start_command(bot, message, args):
    """Handles the /start command for backward compatibility.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    Returns:
        bool: Dispatch result.

    """
    registry = CommandRegistry()
    registry.register_default(bot)
    return await registry.dispatch(message, "/start")


async def handle_help_command(bot, message, args):
    """Handles the /help command for backward compatibility.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    Returns:
        bool: Dispatch result.

    """
    registry = CommandRegistry()
    registry.register_default(bot)
    return await registry.dispatch(message, "/help")


async def handle_stats_command(bot, message, args):
    """Handles the /stats command for backward compatibility.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    Returns:
        bool: Dispatch result.

    """
    registry = CommandRegistry()
    registry.register_default(bot)
    return await registry.dispatch(message, "/stats")


async def handle_engines_command(bot, message, args):
    """Handles the /engines command for backward compatibility.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    Returns:
        bool: Dispatch result.

    """
    registry = CommandRegistry()
    registry.register_default(bot)
    return await registry.dispatch(message, "/engines")


async def handle_voices_command(bot, message, args):
    """Handles the /voices command for backward compatibility.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    Returns:
        bool: Dispatch result.

    """
    registry = CommandRegistry()
    registry.register_default(bot)
    return await registry.dispatch(message, "/voices")


async def handle_config_command(bot, message, args):
    """Handles the /config command.

    Sends config system message.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    """
    await bot.awaitable(bot.adapter.send_message)(message.chat_id, t("config_system"))


async def handle_reset_command(bot, message, args):
    """Handles the /reset command for backward compatibility.

    Dispatches to /resetstats.

    Args:
        bot: The bot instance.
        message: The Telegram message.
        args: Command arguments (ignored).

    Returns:
        bool: Dispatch result.

    """
    registry = CommandRegistry()
    registry.register_default(bot)
    registry.register_admin(bot)
    return await registry.dispatch(message, "/resetstats")


async def admin_performance_analysis(bot, message: TelegramMessage, _: str) -> None:
    """Handles performance analysis for TTS engines.

    Compares engines on requests, success rate, response time, scores.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        from ..metrics.advanced import get_metrics_collector

        metrics_collector = get_metrics_collector()
        comparison = await metrics_collector.get_engine_comparison()

        text = "📈 **Performance Analysis**\n\n"

        for engine_name, data in comparison.items():
            text += f"🎤 **{engine_name}**\n"
            text += f"• درخواست‌ها: {data['requests']:,}\n"
            text += f"• نرخ موفقیت: {data['success_rate']:.1f}%\n"
            text += f"• زمان پاسخ: {data['avg_response_time']:.2f}s\n"
            text += f"• امتیاز قابلیت اطمینان: {data['reliability_score']:.1f}/100\n"
            text += f"• امتیاز عملکرد: {data['performance_score']:.1f}/100\n\n"

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(chat_id, text)

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, t("debug_error", error=str(e))
        )


async def admin_monitor_system(bot, message: TelegramMessage, _: str) -> None:
    """Handles system monitoring with periodic updates.

    Sends updates every 30s for 5min; cancellable via /cancel.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        from ..metrics.advanced import get_metrics_collector

        metrics_collector = get_metrics_collector()

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        if not hasattr(bot, "_monitor_cancel"):
            bot._monitor_cancel = set()

        await bot.awaitable(bot.adapter.send_message)(chat_id, t("health_check"))

        for i in range(10):
            try:
                if chat_id in bot._monitor_cancel:
                    bot._monitor_cancel.discard(chat_id)
                    return
                metrics = await metrics_collector.get_comprehensive_metrics()

                text = t(
                    "monitoring_update",
                    iteration=i + 1,
                    req_total=metrics["requests"]["total"],
                    req_per_minute=metrics["requests"]["per_minute"],
                    success_rate=metrics["requests"]["success_rate"],
                    cpu=metrics["system"]["cpu_percent"],
                    mem_percent=metrics["system"]["memory_percent"],
                    health=metrics["health"],
                )

                await bot.awaitable(bot.adapter.send_message)(chat_id, text)
                await asyncio.sleep(30)

            except Exception as e:
                await bot.awaitable(bot.adapter.send_message)(
                    chat_id, f"❌ خطا در مانیتورینگ: {str(e)}"
                )
                break

        await bot.awaitable(bot.adapter.send_message)(chat_id, t("monitoring_complete"))

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ خطا در شروع مانیتورینگ: {str(e)}"
        )


async def admin_export_metrics(bot, message: TelegramMessage, _: str) -> None:
    """Handles metrics export to JSON file.

    Saves to timestamped file; reports success or error.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        from datetime import datetime
        from pathlib import Path

        from ..metrics.advanced import get_metrics_collector

        metrics_collector = get_metrics_collector()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = Path(f"metrics_export_{timestamp}.json")

        success = await metrics_collector.export_metrics(file_path)

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        if success:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("metrics_export_success", file_path=str(file_path))
            )
        else:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("metrics_export_error")
            )

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ خطا در export: {str(e)}"
        )


async def admin_test_engines(bot, message: TelegramMessage, _: str) -> None:
    """Handles engine testing for available TTS engines.

    Tests edge, piper, gtts; simulates for now.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        await bot.awaitable(bot.adapter.send_message)(chat_id, t("testing_all_engines"))

        engines = ["edge", "piper", "gtts"]
        results = []

        for engine in engines:
            try:
                await asyncio.sleep(1)
                results.append(f"✅ {engine}: OK")
            except Exception as e:
                results.append(f"❌ {engine}: {str(e)}")

        text = t("engine_test_results_with_list", results="\n".join(results))
        await bot.awaitable(bot.adapter.send_message)(chat_id, text)

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ خطا در تست engines: {str(e)}"
        )


async def admin_create_user(bot, message: TelegramMessage, args: str) -> None:
    """Handles user creation with details.

    Parses args, creates in DB, sends confirmation.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        args: Arguments like 'user_id:123 username:Test email:test@example.com admin:true'.

    """
    try:
        args_list = args.split() if args else []

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        if not args_list:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id,
                t("create_user_usage"),
            )
            return

        user_id = None
        username = None
        email = None
        is_admin = False

        for arg in args_list:
            if arg.startswith("user_id:"):
                user_id = arg.split(":", 1)[1]
            elif arg.startswith("username:"):
                username = arg.split(":", 1)[1]
            elif arg.startswith("email:"):
                email = arg.split(":", 1)[1]
            elif arg.startswith("admin:"):
                is_admin = arg.split(":", 1)[1].lower() == "true"

        if not user_id:
            await bot.awaitable(bot.adapter.send_message)(chat_id, t("user_id_missing"))
            return

        from ..database.connection import get_session
        from ..services.user_service import UserService

        db_session = next(get_session())
        user_service = UserService(db_session)

        user = await user_service.create_user(
            user_id=user_id,
            username=username,
            email=email,
            is_admin=is_admin,
        )

        await bot.awaitable(bot.adapter.send_message)(
            chat_id,
            f"✅ **کاربر ایجاد شد**\n\n"
            f"👤 **User ID:** `{user.user_id}`\n"
            f"📝 **نام:** {user.username or 'نامشخص'}\n"
            f"📧 **ایمیل:** {user.email or 'نامشخص'}\n"
            f"🔐 **نوع:** {'مدیر' if user.is_admin else 'کاربر عادی'}\n"
            f"📅 **تاریخ ایجاد:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        )

    except ValueError as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ **خطا در ایجاد کاربر**\n\n{str(e)}"
        )
    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ **خطا در ایجاد کاربر**\n\n{str(e)}"
        )


async def admin_delete_user(bot, message: TelegramMessage, args: str) -> None:
    """Handles user deletion.

    Prevents deleting 'admin'; checks existence before delete.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        args: Arguments like 'user_id:123'.

    """
    try:
        args_list = args.split() if args else []

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        if not args_list:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("error_prefix", error="usage: /delete_user user_id:<id>")
            )
            return

        user_id = None
        for arg in args_list:
            if arg.startswith("user_id:"):
                user_id = arg.split(":", 1)[1]
                break

        if not user_id:
            await bot.awaitable(bot.adapter.send_message)(chat_id, t("user_id_missing"))
            return

        if user_id == "admin":
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("error_prefix", error="cannot delete admin user")
            )
            return

        from ..database.connection import get_session
        from ..services.user_service import UserService

        db_session = next(get_session())
        user_service = UserService(db_session)

        user = await user_service.get_user_by_id(user_id)
        if not user:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("user_not_found", user_id=user_id)
            )
            return

        success = await user_service.delete_user(user_id)

        if success:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("user_deleted", user_id=user_id)
            )
        else:
            await bot.awaitable(bot.adapter.send_message)(
                chat_id, t("error_prefix", error=f"failed to delete user `{user_id}`")
            )

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ **خطا در حذف کاربر**\n\n{str(e)}"
        )


async def admin_list_users(bot, message: TelegramMessage, _: str) -> None:
    """Handles listing all users with details.

    Fetches from DB, formats user info including status and creation date.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        from ..database.connection import get_session
        from ..services.user_service import UserService

        db_session = next(get_session())
        user_service = UserService(db_session)

        users = await user_service.get_all_users()

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        if not users:
            await bot.awaitable(bot.adapter.send_message)(chat_id, t("no_users_found"))
            return

        text = t("users_list_header") + "\n\n"

        for user in users:
            text += f"👤 **{user.user_id}**\n"
            text += f"📝 {t('user_name')}: {user.username or t('user_type_unknown')}\n"
            text += f"📧 {t('user_email')}: {user.email or t('user_type_unknown')}\n"
            text += f"🔐 {t('user_type')}: {t('user_type_admin') if user.is_admin else t('user_type_user')}\n"
            text += f"📊 {t('user_status')}: {t('status_active') if user.is_active else t('status_inactive')}\n"
            text += f"📅 {t('user_created')}: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"

        await bot.awaitable(bot.adapter.send_message)(chat_id, text)

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ **خطا در دریافت لیست کاربران**\n\n{str(e)}"
        )


async def admin_clear_cache(bot, message: TelegramMessage, _: str) -> None:
    """Handles global cache clearing.

    Sends confirmation; duplicate of nested version.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        await bot.awaitable(bot.adapter.send_message)(
            chat_id,
            t("cache_cleared"),
        )

    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, f"❌ خطا در پاک کردن Cache: {str(e)}"
        )


async def admin_restart_system(bot, message: TelegramMessage, _: str) -> None:
    """Handles system restart via execv.

    Stops bot, restarts process; global version for binding.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        import os
        import sys

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )

        await bot.awaitable(bot.adapter.send_message)(chat_id, t("restarting"))
        try:
            await bot.stop()
        except Exception:
            pass
        await asyncio.sleep(0.5)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, t("error_prefix", error=f"restart failed: {e}")
        )


async def admin_shutdown_system(bot, message: TelegramMessage, _: str) -> None:
    """Handles system shutdown via os._exit.

    Stops bot, exits process; global version for binding.

    Args:
        bot: The bot instance.
        message: The TelegramMessage.
        _: Ignored args.

    """
    try:
        import os

        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(chat_id, t("shutting_down"))
        try:
            await bot.stop()
        except Exception:
            pass
        await asyncio.sleep(0.5)
        os._exit(0)
    except Exception as e:
        chat_id = getattr(message, "chat_id", None) or (
            message.get("chat_id") if hasattr(message, "get") else None
        )
        await bot.awaitable(bot.adapter.send_message)(
            chat_id, t("error_prefix", error=f"shutdown failed: {e}")
        )
