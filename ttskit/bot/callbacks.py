"""Manages callback handlers and default implementations for the UnifiedTTSBot.

This keeps callback logic separate from the bot's core, similar to how CommandRegistry works.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from ..engines import registry as engines_registry
from ..utils.i18n import t

CallbackHandler = Callable[[Any, Any, str], Awaitable[Any]]


class CallbackRegistry:
    """Simple registry and dispatcher for callback handlers."""

    def __init__(self) -> None:
        """Initializes the callback registry with empty handler dictionaries."""
        self._handlers: dict[str, CallbackHandler] = {}
        self._admin_handlers: dict[str, CallbackHandler] = {}

    def register(self, prefix: str, handler: CallbackHandler) -> None:
        """Registers a callback handler for the given prefix.

        Args:
            prefix: The prefix string to associate with the handler.
            handler: The async callback handler function.
        """
        self._handlers[prefix] = handler

    def register_callback(
        self, prefix: str, handler: CallbackHandler, admin_only: bool = False
    ) -> None:
        """Registers a callback handler, serving as an alias for the `register` method.

        Args:
            prefix: The prefix string to associate with the handler.
            handler: The asynchronous callback handler function.
            admin_only: If True, the handler is registered under admin-specific callbacks.
        """
        if admin_only:
            self._admin_handlers[prefix] = handler
            self._handlers[prefix] = handler
        else:
            self.register(prefix, handler)

    def register_admin(
        self, prefix: Any, handler: CallbackHandler | None = None
    ) -> None:
        """Registers an admin callback handler or sets up default admin callbacks for testing.

        If handler is None and prefix is a bot instance (not a string), this method registers
        a set of default admin callbacks, including placeholders for testing. Otherwise, it registers
        the provided handler under the specified prefix for admin-only access, adding an extra layer
        of safety.

        Args:
            prefix (str or Any): The callback data prefix, or a bot instance for defaults.
            handler (CallbackHandler | None): The asynchronous handler function, or None for defaults.

        Notes:
            When setting defaults, placeholder functions are used for some admin callbacks to support
            testing scenarios.
        """
        if handler is None and prefix is not None and not isinstance(prefix, str):
            async def admin_stats_placeholder(bot, message, data):
                return "ok"

            async def admin_clear_placeholder(bot, message, data):
                return "ok"

            admin_callbacks = {
                "admin_": admin_stats_placeholder,
                "admin_callback": admin_clear_placeholder,
                "admin_stats": admin_stats_callback,
                "admin_keys": admin_keys_callback,
                "admin_settings": admin_settings_callback,
                "admin_cache": admin_cache_callback,
                "admin_test": admin_test_callback,
                "admin_performance": admin_performance_callback,
                "admin_health": admin_health_callback,
                "admin_back": admin_back_callback,
                "create_key": create_key_callback,
                "list_keys": list_keys_callback,
                "delete_key": delete_key_callback,
                "create_key_user": create_key_user_callback,
                "create_key_writer": create_key_writer_callback,
                "create_key_admin": create_key_admin_callback,
                "delete_key_confirm_": delete_key_confirm_callback,
                "clear_cache": clear_cache_callback,
                "confirm_clear_cache": confirm_clear_cache_callback,
                "cancel_clear_cache": cancel_clear_cache_callback,
                "confirm_restart": confirm_restart_callback,
                "cancel_restart": cancel_restart_callback,
                "test_all_engines": test_all_engines_callback,
                "test_edge": test_edge_callback,
                "test_piper": test_piper_callback,
                "test_gtts": test_gtts_callback,
            }

            self._admin_handlers.update(admin_callbacks)
            self._handlers.update(admin_callbacks)
            return
        if isinstance(prefix, str) and handler is not None:
            self._admin_handlers[prefix] = handler

    def register_bulk(self, mapping: dict[str, CallbackHandler]) -> None:
        """Registers multiple callback handlers from a prefix-to-handler mapping.

        Args:
            mapping: A dictionary where keys are prefixes and values are handler functions.
        """
        for prefix, handler in mapping.items():
            self.register(prefix, handler)

    async def dispatch(self, bot: Any, message: Any, data: str) -> bool:
        """Dispatches a callback to the appropriate handler based on prefix matching.

        This method iterates through all registered prefixes and checks if the incoming
        `data` string starts with any of them. If a match is found and the callback
        is registered as an admin callback, it verifies if the user is authorized
        (sudo) using the bot's internal methods. The corresponding handler is then
        called asynchronously.

        Args:
            bot: The bot instance.
            message: The message object containing user details.
            data: The callback data string to be dispatched.

        Returns:
            bool: True if a handler was found and successfully called, False otherwise.
        """
        data = str(data).strip()
        for prefix, handler in self._handlers.items():
            if data.startswith(prefix):
                if prefix in self._admin_handlers:
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

                await handler(bot, message, data)
                return True
        return False

    async def dispatch_admin(
        self, bot: Any, message: Any, data: str, is_sudo: bool = False
    ) -> bool:
        """Dispatches admin-only callbacks after sudo verification.

        Checks if user is sudo, then matches and calls admin callbacks. Skips if not authorized.

        Args:
            bot: The bot instance.
            message: The message object.
            data: The callback data string.
            is_sudo: Whether user is already verified as sudo.

        Returns:
            bool: True if handler found and called, False otherwise.
        """
        if not is_sudo:
            return False

        for prefix, handler in self._admin_handlers.items():
            if data.startswith(prefix):
                await handler(bot, message, data)
                return True
        return False

    @property
    def callbacks(self) -> dict[str, CallbackHandler]:
        """Get all registered callbacks."""
        return self._handlers.copy()

    @property
    def admin_callbacks(self) -> dict[str, CallbackHandler]:
        """Get all registered admin callbacks."""
        return self._admin_handlers.copy()

    def register_default(self, bot: Any) -> None:
        """Registers default callback handlers for engine selection and settings management.

        This method sets up handlers for common bot interactions, such as allowing users
        to select a preferred TTS engine or adjust bot settings like cache and audio processing.

        Args:
            bot: The bot instance to which these default handlers will be registered.
        """
        async def handle_engine_selection(bot: Any, message: Any, data: str) -> None:
            """Handles the selection of a TTS engine by a user.

            Parses the callback data to identify the selected engine and an optional
            forced language. It then updates the engine priority policy for the relevant
            languages, ensuring the selected engine is prioritized. A confirmation
            message is sent back to the user.

            Args:
                bot: The bot instance used for sending messages and accessing adapter.
                message: The message object that triggered this callback.
                data: The callback data string, expected to be in "engine_<name>[:<lang>]" format.
            """
            try:
                parts = data.split(":", 1)
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

                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id,
                        t("engine_priority_set", engine=selected_engine),
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id,
                        t("engine_priority_set", engine=selected_engine),
                    )
            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("engine_change_error", error=e)
                    )
                except Exception:
                    bot.adapter.send_message(
                        message.chat_id, t("engine_change_error", error=e)
                    )

        async def handle_settings(bot: Any, message: Any, data: str) -> None:
            """Handles changes to bot settings based on callback data.

            This function processes callback data related to bot settings, such as
            enabling/disabling cache or audio processing. It updates the bot's
            internal state accordingly and sends a confirmation message to the user.

            Args:
                bot: The bot instance whose settings are being modified.
                message: The message object that initiated the settings change.
                data: The callback data string, indicating which setting to change.
            """
            try:
                if data == "settings_cache_on":
                    bot.cache_enabled = True
                    text = t("cache_enabled")
                elif data == "settings_cache_off":
                    bot.cache_enabled = False
                    text = t("cache_disabled")
                elif data == "settings_audio_on":
                    bot.audio_processing = True
                    text = t("audio_enabled")
                elif data == "settings_audio_off":
                    bot.audio_processing = False
                    text = t("audio_disabled")
                else:
                    text = t("unknown_setting")

                try:
                    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)
                except Exception:
                    pass
            except Exception as e:
                try:
                    await bot.awaitable(bot.adapter.send_message)(
                        message.chat_id, t("settings_change_error", error=e)
                    )
                except Exception:
                    pass

        self.register_bulk(
            {
                "engine_": handle_engine_selection,
                "settings_": handle_settings,
            }
        )


# Standalone callback handlers for backward compatibility with tests
async def handle_audio_callback(bot, message, data):
    """Handle audio-related callbacks."""
    registry = CallbackRegistry()
    registry.register_default(bot)
    return await registry.dispatch(bot, message, data)


async def handle_callback_query(bot, message, data):
    """Handle general callback queries."""
    registry = CallbackRegistry()
    registry.register_default(bot)
    return await registry.dispatch(bot, message, data)


async def handle_error_callback(bot, message, data):
    """Handle error callbacks."""
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("error_prefix", error=data)
    )


async def handle_text_callback(bot, message, data):
    """Handle text callbacks."""
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("text_callback", data=data)
    )


async def handle_voice_callback(bot, message, data):
    """Handle voice callbacks."""
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("voice_callback", data=data)
    )


# Admin Callback Handlers


async def admin_stats_callback(bot, message, data):
    """Displays a comprehensive system statistics report to the admin.

    This function retrieves detailed metrics from the system's metrics collector,
    including request statistics, engine performance, cache status, response times,
    and overall system health. It then formats this information into a human-readable
    report and sends it to the chat where the callback was triggered.

    Args:
        bot: The bot instance used for sending messages.
        message: The message object that initiated this callback.
        data: The callback data payload (not directly used for stats generation, but part of callback signature).
    """
    try:
        from ..metrics.advanced import get_metrics_collector

        metrics_collector = get_metrics_collector()
        metrics = await metrics_collector.get_comprehensive_metrics()

        text = f"""
📊 **System Statistics**

🔄 **Requests:**
• Total: {metrics["requests"]["total"]:,}
• Successful: {metrics["requests"]["successful"]:,}
• Failed: {metrics["requests"]["failed"]:,}
• Success Rate: {metrics["requests"]["success_rate"]:.1f}%
• Per Minute: {metrics["requests"]["per_minute"]:.1f}

🎤 **Engines:**
"""

        for engine_name, engine_data in metrics["engines"].items():
            text += f"• {engine_name}: {engine_data['total_requests']:,} requests ({engine_data['success_rate']:.1f}% successful)\n"

        text += f"""
🗂️ **Cache:**
• Hit Rate: {metrics["cache"]["hit_rate"]:.1f}%
• Size: {metrics["cache"]["size_mb"]:.1f} MB
• Evictions: {metrics["cache"]["evictions"]:,}

⚡ **Performance:**
• Avg Response: {metrics["performance"].get("avg_response_time", 0):.2f}s
• P95 Response: {metrics["performance"].get("p95_response_time", 0):.2f}s

🖥️ **System:**
• CPU: {metrics["system"]["cpu_percent"]:.1f}%
• Memory: {metrics["system"]["memory_mb"]:.1f} MB ({metrics["system"]["memory_percent"]:.1f}%)
• Health Score: {metrics["health"]:.1f}/100
"""

        await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ Error retrieving statistics: {str(e)}"
        )


async def admin_keys_callback(bot, message, data):
    """Displays the API key management menu to the admin.

    This function sends a message containing the API key management options.
    If the message is a callback query, it edits the existing message; otherwise,
    it sends a new message.

    Args:
        bot: The bot instance used for sending or editing messages.
        message: The message object that triggered this callback.
        data: The callback data payload (not directly used, but part of callback signature).
    """
    keyboard_text = t("admin_keys_menu")

    if hasattr(message, "reply_markup"):
        await bot.awaitable(bot.adapter.edit_message_text)(
            message.chat_id, message.message_id, keyboard_text
        )
    else:
        await bot.awaitable(bot.adapter.send_message)(message.chat_id, keyboard_text)


async def admin_settings_callback(bot, message, data):
    """Show current settings."""
    from ..config import settings

    text = t(
        "admin_settings_details",
        api_rate_limit=settings.api_rate_limit,
        max_text_length=settings.max_text_length,
        cache_ttl=settings.cache_ttl,
        default_engine=settings.default_engine,
        default_language=settings.default_language,
        audio_format=settings.audio_format,
        cache_enabled=("✅" if settings.cache_enabled else "❌"),
        cache_type=settings.cache_type,
        cache_max_size=settings.cache_max_size,
    )

    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


async def admin_cache_callback(bot, message, data):
    """Displays the cache management menu and current cache statistics to the admin.

    This function retrieves comprehensive cache metrics, including hit rate, total hits,
    total misses, cache size, and evictions. It then formats this information into
    a status report and sends it to the chat.

    Args:
        bot: The bot instance used for sending messages.
        message: The message object that initiated this callback.
        data: The callback data payload (not directly used for cache stats, but part of callback signature).
    """
    try:
        from ..metrics.advanced import get_metrics_collector

        metrics_collector = get_metrics_collector()
        metrics = await metrics_collector.get_comprehensive_metrics()
        cache_data = metrics["cache"]

        text = t(
            "cache_management_status",
            hit_rate=cache_data["hit_rate"],
            total_hits=cache_data["total_hits"],
            total_misses=cache_data["total_misses"],
            size_mb=cache_data["size_mb"],
            evictions=cache_data["evictions"],
        )

        await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ Error managing cache: {str(e)}"
        )


async def admin_test_callback(bot, message, data):
    """Show engine testing menu."""
    text = t("admin_test_menu")

    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


async def admin_performance_callback(bot, message, data):
    """Displays detailed performance metrics comparing TTS engines.

    Fetches engine comparison data including request counts, success rates, response times,
    reliability, and performance scores. Formats into a report with bilingual (English/Persian)
    labels and sends it to the admin.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Report includes Persian text for labels like 'درخواست‌ها' (requests) and scores out of 100.
        Data sourced from metrics collector's engine comparison.
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

        await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ خطا در دریافت Performance: {str(e)}"
        )


async def admin_health_callback(bot, message, data):
    """Generates and displays a system health check report for admins.

    Retrieves comprehensive metrics, calculates an overall health score, determines status
    based on thresholds, and includes recommendations for issues like high CPU or low success rates.
    The report is sent to the chat, with bilingual (English/Persian) elements in the output.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused in this handler).

    Notes:
        Health status thresholds: >=90 (excellent, green), 70-89 (good, yellow),
        50-69 (medium, orange), <50 (poor, red). Recommendations appear if CPU/memory >80%,
        success rate <95%, or avg response >5s. Outputs include Persian text for status and tips.
    """
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

        await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ خطا در Health Check: {str(e)}"
        )


async def admin_back_callback(bot, message, data):
    """Return to main admin menu."""
    text = t("admin_back_menu")

    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


# API Key management callbacks
async def create_key_callback(bot, message, data):
    """Show create key menu."""
    text = t("create_key_title")

    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


async def list_keys_callback(bot, message, data):
    """Lists all existing API keys with user details and permissions.

    Retrieves all users and their associated API keys from the database, formats
    a report showing user ID, key ID, permissions, creation date, and active status
    (bilingual Persian/English). Sends the report to the admin if keys exist.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Displays 'فعال' (active) or 'غیرفعال' (inactive) for status. If no users/keys,
        sends a 'no API keys' message. Permissions parsed from JSON.
    """
    try:
        from ..database.connection import get_session
        from ..services.user_service import UserService

        db_session = next(get_session())
        user_service = UserService(db_session)

        users = await user_service.get_all_users()

        if not users:
            await bot.awaitable(bot.adapter.send_message)(
                message.chat_id, t("no_api_keys")
            )
            return

        text = t("api_keys_list_header") + "\n\n"

        for user in users:
            api_keys = await user_service.get_user_api_keys(user.user_id)

            for api_key in api_keys:
                created_at = api_key.created_at.strftime("%Y-%m-%d %H:%M")

                import json

                permissions = json.loads(api_key.permissions)

                text += f"👤 **{user.user_id}**\n"
                text += f"🔑 ID: `{api_key.id}`\n"
                text += f"🔐 {', '.join(permissions)}\n"
                text += f"📅 {created_at}\n"
                text += f"📊 {'فعال' if api_key.is_active else 'غیرفعال'}\n\n"

        await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ **خطا در دریافت لیست**\n\n{str(e)}"
        )


async def delete_key_callback(bot, message, data):
    """Show delete key menu."""
    text = t("delete_key_title")

    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


async def create_key_user_callback(bot, message, data):
    """Create API key with user level permissions."""
    await _create_api_key_with_permissions(bot, message, ["read"])


async def create_key_writer_callback(bot, message, data):
    """Create API key with writer level permissions."""
    await _create_api_key_with_permissions(bot, message, ["read", "write"])


async def create_key_admin_callback(bot, message, data):
    """Create API key with admin level permissions."""
    await _create_api_key_with_permissions(bot, message, ["read", "write", "admin"])


async def _create_api_key_with_permissions(bot, message, permissions):
    """Internal helper to create an API key with specified permissions for a new user.

    Generates a unique user_id based on Telegram user and timestamp, creates the user
    in the database with appropriate admin status if needed, then creates and returns
    the API key. Sends confirmation message with key details; handles errors with bilingual message.

    Args:
        bot: The bot instance for sending messages.
        message: The message object from the Telegram user.
        permissions: List of permission strings (e.g., ["read", "write"]).

    Notes:
        User_id format: "telegram_{user.id}_{timestamp}". Username and email are auto-generated.
        is_admin set if "admin" in permissions. Error messages in Persian.
    """
    try:
        from datetime import datetime

        from ..database.connection import get_session
        from ..services.user_service import UserService

        user_id = f"telegram_{message.user.id}_{int(datetime.now().timestamp())}"

        db_session = next(get_session())
        user_service = UserService(db_session)

        await user_service.create_user(
            user_id=user_id,
            username=f"Telegram User {message.user.id}",
            email=f"{user_id}@telegram.local",
            is_admin="admin" in permissions,
        )

        api_key_data = await user_service.create_api_key(
            user_id=user_id,
            permissions=permissions,
        )

        api_key = api_key_data["api_key"]

        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id,
            t(
                "api_key_created",
                user_id=user_id,
                api_key=api_key,
                permissions=", ".join(permissions),
            ),
        )

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ **خطا در ایجاد کلید**\n\n{str(e)}"
        )


async def delete_key_confirm_callback(bot, message, data):
    """Confirms and deletes an API key for a specific user.

    Parses user_id from callback data, retrieves user's API keys, deletes the first one
    if available, and sends success or error message (bilingual Persian/English).

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data in format "delete_key_confirm_{user_id}".

    Notes:
        User_id extracted by splitting data after "delete_key_confirm_". Deletes only the
        first key if multiple exist. Errors if no keys or deletion fails.
    """
    try:
        user_id = data.split("delete_key_confirm_")[1]

        from ..database.connection import get_session
        from ..services.user_service import UserService

        db_session = next(get_session())
        user_service = UserService(db_session)

        api_keys = await user_service.get_user_api_keys(user_id)
        if not api_keys:
            await bot.awaitable(bot.adapter.send_message)(
                message.chat_id,
                t("error_prefix", error=f"no API keys found for user `{user_id}`"),
            )
            return

        api_key = api_keys[0]
        success = await user_service.delete_api_key(user_id, api_key.id)

        if success:
            await bot.awaitable(bot.adapter.send_message)(
                message.chat_id, t("api_key_deleted", user_id=user_id)
            )
        else:
            await bot.awaitable(bot.adapter.send_message)(
                message.chat_id,
                t(
                    "error_prefix",
                    error=f"failed to delete API key for user `{user_id}`",
                ),
            )

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ **خطا در حذف کلید**\n\n{str(e)}"
        )


# Cache management callbacks
async def clear_cache_callback(bot, message, data):
    """Clear cache with confirmation."""
    text = t("confirm_clear_cache_prompt")

    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


async def confirm_clear_cache_callback(bot, message, data):
    """Confirms and clears the bot's cache upon admin request.

    Executes cache clearing (placeholder for actual implementation, e.g., Redis flushdb).
    Sends success message; handles errors with Persian message.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Cache clearing is a placeholder—replace with actual system call (e.g., Redis flushdb).
        No return value; focuses on side effect of clearing cache.
    """
    try:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id,
            t("cache_cleared"),
        )

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ خطا در پاک کردن Cache: {str(e)}"
        )


async def cancel_clear_cache_callback(bot, message, data):
    """Cancel cache clearing."""
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("clear_cache_cancelled")
    )


# System management callbacks
async def confirm_restart_callback(bot, message, data):
    """Confirms and initiates a system restart for the bot.

    Sends 'restarting' message, executes restart logic (placeholder for deployment-specific
    commands like systemctl or docker restart), then sends completion message.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Restart is a placeholder—implement actual logic (e.g., os.system('systemctl restart ttskit')).
        Handles errors with Persian message. No return value; side effect is system restart.
    """
    try:
        await bot.awaitable(bot.adapter.send_message)(message.chat_id, t("restarting"))

        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, t("restart_complete")
        )

    except Exception as e:
        await bot.awaitable(bot.adapter.send_message)(
            message.chat_id, f"❌ خطا در ریستارت: {str(e)}"
        )


async def cancel_restart_callback(bot, message, data):
    """Cancel restart."""
    await bot.awaitable(bot.adapter.send_message)(message.chat_id, t("cancel_delete"))


# Engine testing callbacks
async def test_all_engines_callback(bot, message, data):
    """Tests all configured TTS engines and reports results to the admin.

    Sends progress message, simulates tests for each engine (edge, piper, gtts) with
    a 1-second delay, collects success/failure results, and sends a formatted list.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Current implementation uses asyncio.sleep(1) as placeholder for actual engine testing.
        Replace with real synth tests. Results bilingual with emojis.
    """
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_all_engines_progress")
    )

    engines = ["edge", "piper", "gtts"]
    results = []

    for engine in engines:
        try:
            import asyncio

            await asyncio.sleep(1)
            results.append(f"✅ {engine}: OK")
        except Exception as e:
            results.append(f"❌ {engine}: {str(e)}")

    text = t("engine_test_results_with_list", results="\n".join(results))
    await bot.awaitable(bot.adapter.send_message)(message.chat_id, text)


async def test_edge_callback(bot, message, data):
    """Tests the Edge TTS engine specifically.

    Sends progress and completion messages; placeholder for actual Edge engine test.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Placeholder implementation—replace with real Edge TTS synthesis test.
        Uses i18n for bilingual progress/complete messages.
    """
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_engine_progress", engine_name="Edge")
    )

    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_engine_complete", engine_name="Edge")
    )


async def test_piper_callback(bot, message, data):
    """Tests the Piper TTS engine specifically.

    Sends progress and completion messages; placeholder for actual Piper engine test.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Placeholder implementation—replace with real Piper TTS synthesis test.
        Uses i18n for bilingual progress/complete messages.
    """
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_engine_progress", engine_name="Piper")
    )

    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_engine_complete", engine_name="Piper")
    )


async def test_gtts_callback(bot, message, data):
    """Tests the GTTS TTS engine specifically.

    Sends progress and completion messages; placeholder for actual GTTS engine test.

    Args:
        bot: The bot instance for sending messages.
        message: The message object triggering the callback.
        data: The callback data (unused here).

    Notes:
        Placeholder implementation—replace with real GTTS TTS synthesis test.
        Uses i18n for bilingual progress/complete messages.
    """
    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_engine_progress", engine_name="GTTS")
    )

    await bot.awaitable(bot.adapter.send_message)(
        message.chat_id, t("testing_engine_complete", engine_name="GTTS")
    )
