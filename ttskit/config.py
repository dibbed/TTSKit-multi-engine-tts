"""
Configuration settings for TTSKit.

This module manages all configuration for TTSKit, loading from environment variables,
validating inputs, and providing defaults. It uses Pydantic v2 for robust handling.
"""

import json
import os
import re
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import ConfigurationError


class Settings(BaseSettings):
    """Configuration settings for the TTSKit application.

    Loads and validates settings from environment variables and .env files.
    Includes options for Telegram integration, TTS engines, API security,
    audio processing, caching, database, and more.

    Notes:
        - Supports multiple TTS engines (Edge, gTTS, Piper) with language-specific policies.
        - Enables fallback between engines for reliability.
        - Includes rate limiting and CORS for API security.
        - Defaults are production-safe but customizable via env vars.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    bot_token: str | None = Field(
        default=None, description="Telegram bot token (required for bot mode)"
    )
    telegram_api_id: int | None = Field(
        default=None, description="Telegram API ID for Pyrogram/Telethon"
    )
    telegram_api_hash: str | None = Field(
        default=None, description="Telegram API Hash for Pyrogram/Telethon"
    )
    telegram_driver: str = Field(
        default="aiogram",
        pattern="^(aiogram|pyrogram|telethon|telebot)$",
        description="Telegram framework driver",
    )

    default_lang: str = Field(
        default="en", description="Default language if not specified"
    )
    max_chars: int = Field(
        default=1000, ge=1, le=10000, description="Maximum characters per request"
    )
    max_text_length: int = Field(
        default=1000, ge=1, le=10000, description="Maximum text length per request"
    )
    tts_default: str = Field(default="edge", description="Default TTS engine")

    api_key: str = Field(default="demo-key", description="API key for authentication")
    api_keys: dict[str, str] = Field(
        default={"demo-user": "demo-key", "admin": "admin-secret"},
        description="Dictionary of user_id -> api_key mappings",
    )
    api_rate_limit: int = Field(
        default=100, ge=1, le=10000, description="API rate limit per minute"
    )
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")
    allowed_hosts: list[str] = Field(
        default=["*"], description="Allowed hosts for security"
    )
    enable_auth: bool = Field(default=False, description="Enable API authentication")
    default_engine: str = Field(default="edge", description="Default TTS engine")
    fallback_enabled: bool = Field(default=True, description="Enable engine fallback")

    default_format: str = Field(default="ogg", description="Default audio format")
    default_bitrate: str = Field(default="48k", description="Default audio bitrate")
    default_sample_rate: int = Field(default=48000, description="Default sample rate")

    health_check_interval: int = Field(
        default=300, description="Health check interval in seconds"
    )
    health_check_timeout: int = Field(
        default=30, description="Health check timeout in seconds"
    )

    version: str = Field(default="1.0.0", description="Application version")

    cache_enabled: bool = Field(default=True, description="Enable caching")

    tts_policy_fa: str = Field(
        default="edge,piper,gtts", description="Engine priority for Persian (fa)"
    )
    tts_policy_en: str = Field(
        default="edge,gtts,piper", description="Engine priority for English (en)"
    )
    tts_policy_ar: str = Field(
        default="edge,gtts,piper", description="Engine priority for Arabic (ar)"
    )

    edge_voice_fa: str = Field(
        default="fa-IR-DilaraNeural", description="Default Edge voice for Persian"
    )
    edge_voice_en: str = Field(
        default="en-US-JennyNeural", description="Default Edge voice for English"
    )
    edge_voice_ar: str = Field(
        default="ar-SA-HamedNeural", description="Default Edge voice for Arabic"
    )

    piper_model_path: str = Field(
        default="./models/piper/", description="Path to Piper voices directory"
    )
    piper_enabled: bool = Field(default=True, description="Enable Piper TTS engine")
    piper_use_cuda: bool = Field(
        default=False, description="Use CUDA for Piper TTS GPU acceleration"
    )
    piper_use_mps: bool = Field(
        default=False, description="Use MPS for Piper TTS Apple Silicon acceleration"
    )

    audio_bitrate: str = Field(
        default="48k",
        pattern="^\\d+k$",
        description="Opus bitrate (e.g., '48k', '64k')",
    )
    audio_sample_rate: int = Field(
        default=48000, ge=8000, le=192000, description="Sample rate in Hz"
    )
    audio_channels: int = Field(
        default=1, ge=1, le=2, description="Audio channels (1=mono, 2=stereo)"
    )
    temp_dir_prefix: str = Field(
        default="ttskit_",
        min_length=1,
        max_length=20,
        description="Prefix for temp directories",
    )

    session_path: str = Field(
        default="./data/sessions/", description="Path to store Telegram sessions"
    )
    data_path: str = Field(
        default="./data/", description="Base path for all data files"
    )
    enable_caching: bool = Field(default=True, description="Enable audio caching")
    cache_ttl: int = Field(
        default=3600, ge=60, le=86400, description="Cache TTL in seconds"
    )

    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_rpm: int = Field(
        default=10, ge=1, le=100, description="Max requests per minute per user"
    )
    rate_limit_window: int = Field(
        default=60, ge=10, le=3600, description="Rate limit window in seconds"
    )
    rate_limit_block_duration: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Block duration in seconds when over limit",
    )

    redis_url: str | None = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching/rate limiting",
    )

    database_url: str | None = Field(
        default=None, description="Database URL (overrides DATABASE_PATH)"
    )
    database_path: str = Field(
        default="./data/ttskit.db", description="SQLite database file path"
    )
    database_echo: bool = Field(
        default=False, description="Enable SQLAlchemy query logging"
    )
    database_pool_size: int = Field(
        default=5, ge=1, le=20, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=10, ge=0, le=50, description="Database max overflow connections"
    )

    api_host: str = Field(default="127.0.0.1", description="API host address")
    api_port: int = Field(default=8080, ge=1, le=65535, description="API port")
    use_api: bool = Field(default=False, description="Use REST API for synthesis")
    api_base_url: str | None = Field(
        default=None,
        description="Base URL of external TTS API (e.g., http://localhost:8000)",
    )
    api_timeout: float = Field(default=15.0, description="API timeout in seconds")

    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str | None) -> str | None:
        """Validate the format of the Telegram bot token.

        Args:
            v: The bot token string to validate, or None.

        Returns:
            The original value if valid or None, unchanged.

        Raises:
            ValueError: If the token doesn't match the expected format (e.g., '123456:ABC...').
        """
        if v is None:
            return v

        if not re.match(r"^\d+:[A-Za-z0-9_-]{35}$", v):
            raise ValueError(
                "Invalid bot token format. Expected format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
            )
        return v

    @field_validator("tts_policy_fa", "tts_policy_en", "tts_policy_ar")
    @classmethod
    def validate_engine_policy(cls, v: str) -> str:
        """Validate the TTS engine policy string for a language.

        Ensures the comma-separated list contains only valid engine names.

        Args:
            v: Comma-separated string of engine names (e.g., 'edge,gtts').

        Returns:
            The original validated string.

        Raises:
            ValueError: If the string is empty or contains invalid engines (must be 'edge', 'gtts', or 'piper').
        """
        if not v.strip():
            return "edge,gtts"

        valid_engines = {"edge", "gtts", "piper"}
        engines = [e.strip() for e in v.split(",")]

        for engine in engines:
            if engine not in valid_engines:
                raise ValueError(
                    f"Invalid engine '{engine}'. Must be one of: {valid_engines}"
                )

        return v

    @field_validator("audio_bitrate")
    @classmethod
    def validate_audio_bitrate(cls, v: str) -> str:
        """Validate the audio bitrate format and range.

        Args:
            v: Bitrate string (e.g., '48k').

        Returns:
            The validated string.

        Raises:
            ValueError: If format is invalid (must end with 'k') or value is outside 32k-320k.
        """
        if not re.match(r"^\d+k$", v):
            raise ValueError('Audio bitrate must be in format like "48k", "64k"')

        bitrate_num = int(v[:-1])
        if bitrate_num < 32 or bitrate_num > 320:
            raise ValueError("Audio bitrate must be between 32k and 320k")

        return v

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, v: str | dict[str, str]) -> dict[str, str]:
        """Validate and parse API keys, accepting dict or JSON string.

        Args:
            v: API keys as a dict (user_id: key) or JSON string.

        Returns:
            Parsed dictionary of user IDs to API keys.

        Raises:
            ValueError: If input is invalid, not a dict/string, or JSON parsing fails.
        """
        if isinstance(v, dict):
            return v

        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, dict):
                    raise ValueError("API_KEYS JSON must contain a dictionary")
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format for API_KEYS: {e}") from e

        raise ValueError("API_KEYS must be a dictionary or JSON string")

    def get_engine_policy(self, lang: str) -> list[str]:
        """Retrieve the prioritized list of TTS engines for a given language.

        Args:
            lang: Language code like 'en', 'fa', or 'ar'.

        Returns:
            List of engine names (e.g., ['edge', 'gtts']) in priority order.

        Notes:
            Defaults to English policy if language is unsupported.
        """
        policy_map = {
            "fa": self.tts_policy_fa,
            "en": self.tts_policy_en,
            "ar": self.tts_policy_ar,
        }

        policy = policy_map.get(lang, self.tts_policy_en)
        return [e.strip() for e in policy.split(",")]

    sudo_users: str = Field(
        default="", description="Comma-separated list of admin user IDs"
    )

    test_bot_token: str = Field(
        default="test_token", description="Bot token for testing purposes"
    )

    @property
    def sudo_user_ids(self) -> set[str]:
        """Get the set of sudo (admin) user IDs from the comma-separated string.

        Returns:
            Set of non-empty, stripped user ID strings.
        """
        return {uid.strip() for uid in self.sudo_users.split(",") if uid.strip()}

    def get_edge_voice_for_language(self, lang: str) -> str:
        """Select the default Edge TTS voice for the given language.

        Args:
            lang: Language code like 'en', 'fa', or 'ar'.

        Returns:
            The voice name string; defaults to English if unsupported.
        """
        voice_map = {
            "fa": self.edge_voice_fa,
            "en": self.edge_voice_en,
            "ar": self.edge_voice_ar,
        }

        return voice_map.get(lang, self.edge_voice_en)

    def get_model_path(self, engine: str) -> str:
        """Retrieve the model directory path for a specific TTS engine.

        Args:
            engine: Name of the engine like 'piper', 'edge', or 'gtts'.

        Returns:
            The path string for Piper models, or empty string for others (online engines don't need local models).
        """
        if engine == "piper":
            return self.piper_model_path
        else:
            return ""

    def ensure_data_directories(self) -> None:
        """Create essential data directories if they don't exist.

        Handles paths for general data, Telegram sessions, Piper models, and database.

        Notes:
            Uses os.makedirs with exist_ok=True to avoid errors if directories already exist.
        """
        import os

        directories = [
            self.data_path,
            self.session_path,
            self.piper_model_path,
            os.path.dirname(self.database_path),
        ]

        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    def is_engine_enabled(self, engine: str) -> bool:
        """Determine if a TTS engine is enabled and included in language policies.

        Args:
            engine: Engine name like 'piper', 'edge', or 'gtts'.

        Returns:
            True if enabled (for Piper: piper_enabled and in policies; for others: in any policy).

        Notes:
            Online engines (edge, gtts) are enabled if mentioned in at least one language policy.
        """
        if engine == "piper":
            return self.piper_enabled and any(
                "piper" in policy
                for policy in [
                    self.tts_policy_fa,
                    self.tts_policy_en,
                    self.tts_policy_ar,
                ]
            )

        all_policies = [self.tts_policy_fa, self.tts_policy_en, self.tts_policy_ar]
        return any(engine in policy for policy in all_policies)


# Global settings instance
settings = Settings()


def get_config_value(key: str, default: Any = None) -> Any:
    """Retrieve a configuration value by its key name.

    Args:
        key: The settings attribute name (e.g., 'bot_token').
        default: Fallback value if key doesn't exist (default: None).

    Returns:
        The value from settings, or the default.
    """
    return getattr(settings, key, default)


def set_config_value(key: str, value: Any) -> None:
    """Dynamically set a configuration value.

    Args:
        key: The settings attribute name to update.
        value: The new value to assign.

    Notes:
        This modifies the global settings instance at runtime.
    """
    setattr(settings, key, value)


def get_all_config() -> dict[str, Any]:
    """Export all current configuration as a dictionary.

    Returns:
        Dict of all settings keys and values, using Pydantic's model_dump().

    Notes:
        Includes defaults and any overrides from env vars.
    """
    return settings.model_dump()


def validate_config() -> bool:
    """Validate the entire configuration setup.

    Returns:
        True if all settings pass validation, False if any fail.

    Notes:
        Recreates Settings with current values to trigger validators.
    """
    try:
        Settings(**settings.model_dump())
        return True
    except Exception:
        return False


def get_settings() -> Settings:
    """Access the global Settings instance.

    Returns:
        The singleton Settings object.

    Notes:
        This is the central configuration holder for the application.
    """
    return settings


def load_config_from_file(file_path: str) -> Settings:
    """Load settings by parsing a config file as key=value pairs.

    Supports simple .env-like files, ignoring comments (#).

    Args:
        file_path: Path to the configuration file.

    Returns:
        A new Settings instance populated from the file.

    Raises:
        ConfigurationError: If file can't be read, parsed, or validation fails.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        env_vars = {}
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

        # Convert string values to appropriate types for Settings
        settings_kwargs = {}
        for key, value in env_vars.items():
            if key == "MAX_TEXT_LENGTH":
                settings_kwargs[key.lower()] = int(value)
            elif key == "CACHE_MAX_SIZE":
                settings_kwargs[key.lower()] = int(value)
            elif key == "ENABLE_RATE_LIMITING":
                settings_kwargs[key.lower()] = value.lower() in ("true", "1", "yes")
            elif key == "REDIS_URL":
                settings_kwargs[key.lower()] = value
            elif key == "BOT_TOKEN":
                settings_kwargs[key.lower()] = value
            elif key == "API_KEYS":
                settings_kwargs[key.lower()] = value
            elif key == "DEFAULT_LANGUAGE":
                settings_kwargs[key.lower()] = value
            elif key == "AUDIO_FORMAT":
                settings_kwargs[key.lower()] = value
            elif key == "CACHE_TYPE":
                settings_kwargs[key.lower()] = value
            elif key == "ENGINE_POLICIES":
                settings_kwargs[key.lower()] = value
            else:
                settings_kwargs[key.lower()] = value

        return Settings(**settings_kwargs)
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load config from file {file_path}: {e}"
        ) from e


def save_config_to_file(file_path: str, config: Settings) -> None:
    """Export the settings to a simple key=value config file.

    Includes a header comment; skips None values.

    Args:
        file_path: Output file path.
        config: The Settings instance to save.

    Raises:
        ConfigurationError: If writing to file fails.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# TTSKit Configuration File\n")
            f.write("# Generated automatically\n\n")

            for field_name in config.model_fields:
                value = getattr(config, field_name)
                if value is not None:
                    f.write(f"{field_name}={value}\n")

    except Exception as e:
        raise ConfigurationError(
            f"Failed to save config to file {file_path}: {e}"
        ) from e


if not settings.bot_token and "BOT_TOKEN" in os.environ:
    settings.bot_token = os.environ["BOT_TOKEN"]
if not settings.telegram_api_id and os.environ.get("TELEGRAM_API_ID"):
    try:
        settings.telegram_api_id = int(os.environ["TELEGRAM_API_ID"])  # type: ignore[assignment]
    except ValueError:
        pass
if not settings.telegram_api_hash and os.environ.get("TELEGRAM_API_HASH"):
    settings.telegram_api_hash = os.environ["TELEGRAM_API_HASH"]

if os.environ.get("TELEGRAM_ADAPTER") and not os.environ.get("TELEGRAM_DRIVER"):
    try:
        settings.telegram_driver = os.environ["TELEGRAM_ADAPTER"]
    except Exception as e:
        from .utils.logging_config import get_logger

        logger = get_logger(__name__)
        logger.warning(f"Failed to set telegram_driver from TELEGRAM_ADAPTER: {e}")

try:
    if os.environ.get("RATE_LIMIT_REQUESTS"):
        settings.rate_limit_rpm = int(os.environ["RATE_LIMIT_REQUESTS"])  # type: ignore[assignment]
    if os.environ.get("RATE_LIMIT_WINDOW"):
        settings.rate_limit_window = int(os.environ["RATE_LIMIT_WINDOW"])  # type: ignore[assignment]
    if os.environ.get("RATE_LIMIT_BLOCK_DURATION"):
        settings.rate_limit_block_duration = int(
            os.environ["RATE_LIMIT_BLOCK_DURATION"]
        )  # type: ignore[assignment]
except Exception as exc:
    from .utils.logging_config import get_logger

    logger = get_logger(__name__)
    logger.warning("Failed to parse legacy rate limit envs: %s", exc)
