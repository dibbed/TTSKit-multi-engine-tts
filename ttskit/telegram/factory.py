"""Telegram adapter factory for TTSKit.

Central factory class for instantiating adapters based on framework type (Aiogram,
Pyrogram, Telebot, Telethon). Supports dependency checking, custom registration,
and global convenience functions for easy creation and validation.
"""

from enum import Enum
from typing import Any

from ..config import settings
from ..utils.logging_config import get_logger
from .aiogram_adapter import AiogramAdapter
from .base import TelegramAdapter
from .pyrogram_adapter import PyrogramAdapter
from .telebot_adapter import TelebotAdapter
from .telethon_adapter import TelethonAdapter

logger = get_logger(__name__)


class AdapterType(Enum):
    """Enumeration of supported Telegram adapter types.

    Defines the frameworks compatible with the factory: Aiogram, Pyrogram, Telethon, Telebot.
    """

    AIOGRAM = "aiogram"
    PYROGRAM = "pyrogram"
    TELETHON = "telethon"
    TELEBOT = "telebot"


class AdapterFactory:
    """Factory class for creating and managing Telegram adapters.

    Allows instantiation of adapters by type, custom registration, dependency
    checks, and info retrieval. Uses a cache for custom overrides.

    Attributes:
        _adapters_cache: Internal dict for registered custom adapters.
    """

    def __init__(self):
        """Initialize the factory with empty custom adapter cache."""
        self._adapters_cache: dict[AdapterType, type] = {}

    def _get_adapters(self) -> dict[AdapterType, type]:
        """Retrieve the merged dictionary of default and custom adapters.

        Defaults are built-in; customs override.

        Returns:
            Dict mapping AdapterType to adapter classes.
        """
        default_adapters = {
            AdapterType.AIOGRAM: AiogramAdapter,
            AdapterType.PYROGRAM: PyrogramAdapter,
            AdapterType.TELETHON: TelethonAdapter,
            AdapterType.TELEBOT: TelebotAdapter,
        }

        return {**default_adapters, **self._adapters_cache}

    def create_adapter(self, adapter_type: AdapterType | str, bot_token: str, **kwargs):
        """Instantiate a Telegram adapter of the specified type.

        Validates type, resolves class (preferring customs), and creates instance.

        Args:
            adapter_type: AdapterType enum or string (e.g., 'aiogram').
            bot_token: The bot token to pass to the adapter.
            **kwargs: Additional keyword args forwarded to the adapter constructor.

        Returns:
            An initialized TelegramAdapter instance.

        Raises:
            ValueError: If type invalid or unsupported.
            Exception: From adapter instantiation (e.g., missing deps).

        Notes:
            String types converted to Enum; customs override defaults.
            Dynamic imports for built-ins to support patching in tests.
        """
        if isinstance(adapter_type, str):
            try:
                adapter_type = AdapterType(adapter_type.lower())
            except ValueError as err:
                available = [t.value for t in self._get_adapters().keys()]
                raise ValueError(
                    f"Adapter type '{adapter_type}' not supported. Available: {available}"
                ) from err

        adapters = self._get_adapters()
        if adapter_type not in adapters:
            available = [t.value for t in adapters.keys()]
            raise ValueError(
                f"Adapter type '{adapter_type.value}' not supported. Available: {available}"
            )

        try:
            if adapter_type in self._adapters_cache:
                adapter_class = self._adapters_cache[adapter_type]
            else:
                if adapter_type == AdapterType.AIOGRAM:
                    from ttskit.telegram.aiogram_adapter import AiogramAdapter

                    adapter_class = AiogramAdapter
                elif adapter_type == AdapterType.PYROGRAM:
                    from ttskit.telegram.pyrogram_adapter import PyrogramAdapter

                    adapter_class = PyrogramAdapter
                elif adapter_type == AdapterType.TELETHON:
                    from ttskit.telegram.telethon_adapter import TelethonAdapter

                    adapter_class = TelethonAdapter
                elif adapter_type == AdapterType.TELEBOT:
                    from ttskit.telegram.telebot_adapter import TelebotAdapter

                    adapter_class = TelebotAdapter
                else:
                    adapter_class = adapters[adapter_type]

            # Auto-inject API credentials for adapters that require MTProto (Pyrogram/Telethon)
            if adapter_type in (AdapterType.PYROGRAM, AdapterType.TELETHON):
                api_id = kwargs.get("api_id") or settings.telegram_api_id
                api_hash = kwargs.get("api_hash") or settings.telegram_api_hash
                if api_id is None or not api_hash:
                    raise ValueError(
                        "Missing Telegram API credentials. Set TELEGRAM_API_ID and TELEGRAM_API_HASH in settings/.env "
                        f"for adapter '{adapter_type.value}'."
                    )
                kwargs["api_id"] = api_id
                kwargs["api_hash"] = api_hash

            adapter = adapter_class(bot_token, **kwargs)
            logger.info(f"Created {adapter_type.value} adapter")
            return adapter
        except Exception as e:
            logger.error(f"Failed to create {adapter_type.value} adapter: {e}")
            raise

    def get_available_adapters(self) -> list[AdapterType]:
        """List all supported adapter types (default + custom).

        Returns:
            List of AdapterType enums available via the factory.
        """
        return list(self._get_adapters().keys())

    # Expose enum on factory for tests referencing adapter_factory.AdapterType
    AdapterType = AdapterType

    def get_adapter_info(self, adapter_type: AdapterType) -> dict[str, Any] | None:
        """Retrieve metadata for a specific adapter type.

        Args:
            adapter_type: The AdapterType to query.

        Returns:
            Dict with type, class name, module, description, and availability;
            None if type not supported.
        """
        adapters = self._get_adapters()
        if adapter_type not in adapters:
            return None

        adapter_class = adapters[adapter_type]

        return {
            "type": adapter_type.value,
            "class": adapter_class.__name__,
            "module": adapter_class.__module__,
            "description": adapter_class.__doc__,
            "available": True,
        }

    def get_all_adapters_info(self) -> dict[str, dict[str, Any]]:
        """Get metadata for every available adapter.

        Returns:
            Dict keyed by type string, values are adapter info dicts.
        """
        return {
            adapter_type.value: self.get_adapter_info(adapter_type)
            for adapter_type in self._get_adapters().keys()
        }

    def register_adapter(
        self, adapter_type: AdapterType, adapter_class: type[TelegramAdapter]
    ) -> None:
        """Register a custom adapter class, overriding default if present.

        Args:
            adapter_type: The AdapterType to associate.
            adapter_class: Subclass of TelegramAdapter to register.

        Notes:
            Stored in cache; takes precedence over built-ins.
        """
        self._adapters_cache[adapter_type] = adapter_class
        logger.info(f"Registered custom adapter: {adapter_type.value}")

    def unregister_adapter(self, adapter_type: AdapterType) -> None:
        """Remove a custom adapter from the cache.

        Args:
            adapter_type: The AdapterType to unregister.

        Notes:
            Only affects customs; defaults remain available.
        """
        if adapter_type in self._adapters_cache:
            del self._adapters_cache[adapter_type]
            logger.info(f"Unregistered adapter: {adapter_type.value}")

    def check_dependencies(self, adapter_type: AdapterType) -> dict[str, bool]:
        """Verify if the Python packages for an adapter are installed.

        Args:
            adapter_type: The AdapterType to check.

        Returns:
            Dict with 'available' bool and optional 'error' string.

        Notes:
            Uses importlib.util.find_spec for non-intrusive checks.
            Defaults to True if no specific check defined.
        """
        adapters = self._get_adapters()
        if adapter_type not in adapters:
            return {"available": False, "error": "Adapter type not supported"}

        try:
            _ = adapters[adapter_type]

            if adapter_type == AdapterType.AIOGRAM:
                import importlib.util

                return {"available": importlib.util.find_spec("aiogram") is not None}

            elif adapter_type == AdapterType.PYROGRAM:
                import importlib.util

                return {"available": importlib.util.find_spec("pyrogram") is not None}

            elif adapter_type == AdapterType.TELETHON:
                import importlib.util

                return {"available": importlib.util.find_spec("telethon") is not None}

            elif adapter_type == AdapterType.TELEBOT:
                import importlib.util

                return {"available": importlib.util.find_spec("telebot") is not None}

            return {"available": True}

        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_recommended_adapter(self) -> AdapterType | None:
        """Find the first available adapter based on dependencies.

        Returns:
            The first AdapterType with available deps, or None if none.

        Notes:
            Order follows _get_adapters keys (defaults first).
        """
        for adapter_type in self._get_adapters().keys():
            deps = self.check_dependencies(adapter_type)
            if deps.get("available", False):
                return adapter_type

        return None

    def get_adapters_by_dependencies(self) -> dict[str, list[AdapterType]]:
        """Group adapters by installation status.

        Returns:
            Dict with 'available' and 'unavailable' lists of AdapterType.
        """
        available = []
        unavailable = []

        for adapter_type in self._get_adapters().keys():
            deps = self.check_dependencies(adapter_type)
            if deps.get("available", False):
                available.append(adapter_type)
            else:
                unavailable.append(adapter_type)

        return {"available": available, "unavailable": unavailable}


# Global factory instance
factory = AdapterFactory()


def create_adapter(adapter_type: str, bot_token: str, **kwargs) -> TelegramAdapter:
    """Convenience function to create an adapter via the global factory.

    Args:
        adapter_type: String type (e.g., 'aiogram').
        bot_token: The bot token.
        **kwargs: Forwarded to adapter constructor.

    Returns:
        Initialized TelegramAdapter.

    Raises:
        ValueError: If type unknown.
    """
    try:
        adapter_enum = AdapterType(adapter_type.lower())
        return factory.create_adapter(adapter_enum, bot_token, **kwargs)
    except ValueError as err:
        available = [t.value for t in factory.get_available_adapters()]
        raise ValueError(
            f"Unknown adapter type: {adapter_type}. Available: {available}"
        ) from err


def get_available_adapters() -> list[str]:
    """List available adapter types as strings via global factory.

    Returns:
        List of type strings (e.g., ['aiogram', 'pyrogram']).
    """
    return [t.value for t in factory.get_available_adapters()]


def get_recommended_adapter() -> str | None:
    """Get the recommended available adapter as string.

    Returns:
        Type string or None if none available.
    """
    recommended = factory.get_recommended_adapter()
    return recommended.value if recommended else None


def check_dependencies(adapter_type: str) -> dict[str, Any]:
    """Check deps for adapter type string via global factory.

    Args:
        adapter_type: String type (e.g., 'telethon').

    Returns:
        Deps dict; error if unknown type.

    Raises:
        No raise; returns error in dict.
    """
    try:
        adapter_enum = AdapterType(adapter_type.lower())
        return factory.check_dependencies(adapter_enum)
    except ValueError:
        return {
            "available": False,
            "error": f"Unknown adapter type: {adapter_type}",
        }


# Alias for backward compatibility
TelegramAdapterFactory = AdapterFactory
