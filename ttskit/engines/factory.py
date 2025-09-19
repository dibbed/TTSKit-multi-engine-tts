"""
Engine Factory for TTSKit.

This module provides a factory for creating and managing TTS engines,
including registration, instantiation, and capability management for
all supported TTS engines.
"""

import builtins as _builtins
from typing import Any

from ..utils.logging_config import get_logger
from .base import EngineCapabilities, TTSEngine
from .edge_engine import EDGE_AVAILABLE as _EDGE_AVAILABLE
from .edge_engine import EdgeEngine
from .gtts_engine import GTTSEngine
from .piper_engine import PIPER_AVAILABLE, PiperEngine
from .registry import EngineRegistry

logger = get_logger(__name__)


class EngineFactory:
    """
    Factory for creating and managing TTS engines.
    
    This class handles registration, creation, and management of TTS engines,
    providing a centralized way to work with different engine implementations
    and their capabilities.
    """

    def __init__(self):
        """
        Initialize the engine factory.
        
        Sets up internal storage for engine classes, configurations, and
        instances, then registers all default engines.
        """
        self.engine_classes: dict[str, type[TTSEngine]] = {}
        self.engine_configs: dict[str, dict[str, Any]] = {}
        self.engines: dict[str, TTSEngine] = {}
        self._register_default_engines()

    def _register_default_engines(self) -> None:
        """
        Register default engines.
        
        Registers GTTS, Edge TTS, and Piper engines with their default
        configurations and capabilities if they are available.
        """
        self.register_engine_class(
            "gtts",
            GTTSEngine,
            {
                "offline": False,
                "ssml": False,
                "rate_control": False,
                "pitch_control": False,
                "languages": [
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
                    "fa",
                ],
                "voices": [],
                "max_text_length": 5000,
            },
        )

        if _EDGE_AVAILABLE:
            self.register_engine_class(
                "edge",
                EdgeEngine,
                {
                    "offline": False,
                    "ssml": True,
                    "rate_control": False,
                    "pitch_control": False,
                    "languages": [
                        "en",
                        "fa",
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
                    ],
                    "voices": [
                        "en-US-JennyNeural",
                        "fa-IR-DilaraNeural",
                        "ar-SA-HamedNeural",
                        "es-ES-ElviraNeural",
                        "fr-FR-DeniseNeural",
                        "de-DE-KatjaNeural",
                        "it-IT-ElsaNeural",
                        "pt-BR-FranciscaNeural",
                        "ru-RU-SvetlanaNeural",
                        "ja-JP-NanamiNeural",
                        "ko-KR-SunHiNeural",
                        "zh-CN-XiaoxiaoNeural",
                    ],
                    "max_text_length": 10000,
                },
            )

        if PIPER_AVAILABLE:
            self.register_engine_class(
                "piper",
                PiperEngine,
                {
                    "offline": True,
                    "ssml": False,
                    "rate_control": True,
                    "pitch_control": False,
                    "languages": [
                        "en",
                        "fa",
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
                    ],
                    "voices": [],
                    "max_text_length": 5000,
                },
            )

    def register_engine_class(
        self, name: str, engine_class: type[TTSEngine], capabilities: dict[str, Any]
    ) -> None:
        """
        Register an engine class.

        Args:
            name: Engine name identifier
            engine_class: Engine class to register
            capabilities: Dictionary describing engine capabilities
        """
        self.engine_classes[name] = engine_class
        self.engine_configs[name] = capabilities
        logger.info(f"Registered engine class: {name}")

    def create_engine(self, name: str, **kwargs) -> TTSEngine:
        """
        Create an engine instance.

        Args:
            name: Engine name to create
            **kwargs: Engine-specific initialization arguments

        Returns:
            Initialized engine instance

        Raises:
            ValueError: If engine class is not registered
        """
        if name not in self.engine_classes:
            available = list(self.engine_classes.keys())
            raise ValueError(f"Engine '{name}' not found. Available: {available}")

        engine_class = self.engine_classes[name]
        engine = engine_class(**kwargs)

        logger.info(f"Created engine instance: {name}")
        return engine

    def get_available_engines(self) -> list[str]:
        """
        Get list of available engine names.

        Returns:
            List of registered engine names
        """
        return list(self.engine_classes.keys())

    def get_engine_capabilities(self, name: str | None = None) -> dict[str, Any] | None:
        """
        Get capabilities for an engine.

        Args:
            name: Engine name, or None to get all engine capabilities

        Returns:
            Engine capabilities dictionary, or dict of all engines if name is None
        """
        if name is None:
            out: dict[str, dict[str, Any]] = {}
            for n, cfg in self.engine_configs.items():
                cfg_copy = dict(cfg)
                cfg_copy.setdefault("rate", cfg_copy.get("rate_control", False))
                cfg_copy.setdefault("pitch", cfg_copy.get("pitch_control", False))
                cfg_copy.setdefault("langs", cfg_copy.get("languages", []))
                out[n] = cfg_copy
            return out
        cfg = self.engine_configs.get(name)
        if cfg is None:
            return None
        return cfg

    def create_all_engines(self, **kwargs) -> dict[str, TTSEngine]:
        """
        Create all available engines.

        Args:
            **kwargs: Common arguments for all engines

        Returns:
            Dictionary mapping engine names to instances
        """
        engines = {}
        for name in self.get_available_engines():
            try:
                engine_kwargs = {}
                if name == "piper":
                    for key in ["model_path", "use_cuda", "use_mps"]:
                        if key in kwargs:
                            engine_kwargs[key] = kwargs[key]
                elif name in ["gtts", "edge"]:
                    for key, value in kwargs.items():
                        if key not in ["model_path", "use_cuda", "use_mps"]:
                            engine_kwargs[key] = value
                else:
                    engine_kwargs = kwargs

                engines[name] = self.create_engine(name, **engine_kwargs)
            except Exception as e:
                logger.warning(f"Failed to create engine {name}: {e}")

        return engines

    def setup_registry(self, registry: EngineRegistry, **kwargs) -> None:
        """
        Setup engine registry with all available engines.

        Args:
            registry: Engine registry instance to populate
            **kwargs: Common arguments for all engines
        """
        from ..config import settings

        engine_kwargs = kwargs.copy()

        if "piper" in self.engine_classes:
            engine_kwargs.update(
                {
                    "model_path": settings.piper_model_path,
                    "use_cuda": settings.piper_use_cuda,
                }
            )

        engines = self.create_all_engines(**engine_kwargs)

        for name, engine in engines.items():
            capabilities_dict = self.get_engine_capabilities(name)
            if capabilities_dict:
                capabilities = EngineCapabilities(**capabilities_dict)
                registry.register_engine(name, engine, capabilities)
                logger.info(f"Registered engine in registry: {name}")

    def get_engine_info(self, name: str | None = None) -> dict[str, Any] | None:
        """
        Get engine information.

        Args:
            name: Engine name, or None to get default engine info

        Returns:
            Engine information dictionary or None if not found
        """
        if name is None:
            if "gtts" in self.engine_classes:
                name = "gtts"
            else:
                available = list(self.engine_classes.keys())
                if not available:
                    return None
                name = available[0]
        if name not in self.engine_classes:
            return None

        capabilities = self.get_engine_capabilities(name)
        if not capabilities:
            return None

        return {
            "name": name,
            "class": self.engine_classes[name].__name__,
            "capabilities": capabilities,
            "available": True,
        }

    def get_all_engines_info(self) -> dict[str, dict[str, Any]]:
        """
        Get information for all engines.

        Returns:
            Dictionary mapping engine names to their information
        """
        return {
            name: self.get_engine_info(name) for name in self.get_available_engines()
        }

    def get_engine(self, name: str, **kwargs) -> TTSEngine | None:
        """
        Get engine instance by name.

        Args:
            name: Engine name to retrieve
            **kwargs: Engine initialization arguments

        Returns:
            Engine instance or None if not found or creation fails
        """
        if name in self.engines:
            return self.engines[name]
        if name not in self.engine_classes:
            known_names = {"gtts", "edge", "piper"}
            if name in known_names:
                return None
            raise ValueError("Unknown engine")
        try:
            engine_kwargs = {}
            if name == "piper":
                for key in ["model_path", "use_cuda", "use_mps"]:
                    if key in kwargs:
                        engine_kwargs[key] = kwargs[key]
            elif name in ["gtts", "edge"]:
                for key, value in kwargs.items():
                    if key not in ["model_path", "use_cuda", "use_mps"]:
                        engine_kwargs[key] = value
            else:
                engine_kwargs = kwargs

            engine = self.create_engine(name, **engine_kwargs)
            if "default_lang" in kwargs and hasattr(engine, "default_lang"):
                try:
                    engine.default_lang = kwargs["default_lang"]
                except Exception as e:
                    logger.warning(f"Failed to set default_lang for {name}: {e}")
            self.engines[name] = engine
            return engine
        except Exception:
            return None

    def list_engines(self) -> list[str]:
        """
        List all available engines.

        Returns:
            List of registered engine names
        """
        return self.get_available_engines()

    def is_engine_available(self, name: str) -> bool:
        """
        Check if engine is available.

        Args:
            name: Engine name to check

        Returns:
            True if engine is registered and available
        """
        return (
            name in self.engine_classes
            or name in self.engines
            or name in self.engine_configs
        )

    def get_recommended_engine(self, language: str = "en") -> str | None:
        """
        Get recommended engine for a language.

        Args:
            language: Language code to get recommendation for

        Returns:
            Recommended engine name or None if no suitable engine found
        """
        if language in [
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
            "fa",
        ]:
            if "edge" in self.engine_classes:
                return "edge"
            elif "gtts" in self.engine_classes:
                return "gtts"
        return None

    def get_engines_by_capability(
        self, capability: str, value: bool | None = None
    ) -> list[str]:
        """
        Get engines that support a specific capability.

        Args:
            capability: Capability name (e.g., 'offline', 'ssml', 'rate_control')
            value: Desired value for capability (defaults to True if None)

        Returns:
            List of engine names that match the capability requirement
        """
        engines = []
        desired = True if value is None else bool(value)
        for name, config in self.engine_configs.items():
            if bool(config.get(capability, False)) == desired:
                engines.append(name)
        return engines

    def get_engines_by_language(self, language: str) -> list[str]:
        """
        Get engines that support a specific language.

        Args:
            language: Language code to check support for

        Returns:
            List of engine names that support the language
        """
        engines = []
        for name, config in self.engine_configs.items():
            if language in config.get("languages", []):
                engines.append(name)
        return engines

    def get_engine_statistics(self) -> dict[str, Any]:
        """
        Get engine statistics.

        Returns:
            Dictionary with comprehensive engine statistics and capabilities
        """
        return {
            "total_engines": len(self.engine_classes),
            "available_engines": len(self.engines),
            "engine_names": list(self.engine_classes.keys()),
            "offline_engines": self.get_engines_by_capability("offline", True),
            "online_engines": self.get_engines_by_capability("offline", False),
            "capabilities": {
                "offline": self.get_engines_by_capability("offline", True),
                "ssml": self.get_engines_by_capability("ssml", True),
                "rate_control": self.get_engines_by_capability("rate_control", True),
                "pitch_control": self.get_engines_by_capability("pitch_control", True),
            },
        }

    def register_engine(
        self, name: str, engine: TTSEngine, capabilities: dict[str, Any] | None = None
    ) -> None:
        """
        Register an engine instance.

        Args:
            name: Engine name identifier
            engine: Engine instance to register
            capabilities: Engine capabilities dictionary
        """
        self.engines[name] = engine
        self.engine_configs[name] = capabilities or {
            "offline": False,
            "ssml": False,
            "rate_control": False,
            "pitch_control": False,
            "languages": [],
            "voices": [],
            "max_text_length": 5000,
        }
        logger.info(f"Registered engine instance: {name}")

    def unregister_engine(self, name: str) -> bool:
        """
        Unregister an engine.

        Args:
            name: Engine name to unregister

        Returns:
            True if engine was successfully unregistered
        """
        if name in self.engines:
            del self.engines[name]
            if name in self.engine_configs:
                del self.engine_configs[name]
            logger.info(f"Unregistered engine: {name}")
            return True
        return False


factory = EngineFactory()


def create_engine(name: str, **kwargs) -> TTSEngine:
    """
    Create an engine instance using the global factory.

    Args:
        name: Engine name to create
        **kwargs: Engine-specific initialization arguments

    Returns:
        Initialized engine instance
    """
    return factory.create_engine(name, **kwargs)


def setup_default_registry(registry: EngineRegistry = None, **kwargs) -> EngineRegistry:
    """
    Setup default engine registry.

    Args:
        registry: Engine registry instance (creates new if None)
        **kwargs: Common arguments for all engines

    Returns:
        Configured engine registry instance
    """
    if registry is None:
        registry = EngineRegistry()

    factory.setup_registry(registry, **kwargs)
    return registry


def get_available_engines() -> list[str]:
    """
    Get list of available engine names.

    Returns:
        List of available engine names from global factory
    """
    return factory.get_available_engines()


EDGE_AVAILABLE = _EDGE_AVAILABLE
_builtins.EDGE_AVAILABLE = EDGE_AVAILABLE


def setup_registry(registry: EngineRegistry, **kwargs) -> None:
    """
    Setup registry using the global factory.
    
    Args:
        registry: Engine registry to configure
        **kwargs: Arguments to pass to engines
    """
    factory.setup_registry(registry, **kwargs)


def get_engine_capabilities(name: str) -> dict[str, Any] | None:
    """
    Get capabilities for an engine.

    Args:
        name: Engine name to get capabilities for

    Returns:
        Engine capabilities dictionary or None if not found
    """
    return factory.get_engine_capabilities(name)
