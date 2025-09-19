"""TTSKit Engine Registry Module.

This module manages a centralized registry for TTS engines, their capabilities, performance metrics, and language-specific routing policies.
It enables dynamic engine selection based on requirements and tracks usage statistics.
"""

from dataclasses import dataclass
from typing import Any

from ..utils.logging_config import get_logger
from .base import EngineCapabilities, TTSEngine

logger = get_logger(__name__)


@dataclass
class LanguagePolicy:
    """Policy configuration for a specific language's engine selection and limits.

    Defines the primary and fallback engines, default voice, text length limit, and rate limiting.

    Attributes:
        primary_engine: The main engine name for this language (str).
        fallback_engines: List of backup engine names (list[str]).
        default_voice: Default voice to use for synthesis (str).
        max_text_length: Maximum characters allowed in text input (int).
        rate_limit_rpm: Requests per minute limit (int).
    """
    primary_engine: str
    fallback_engines: list[str]
    default_voice: str
    max_text_length: int
    rate_limit_rpm: int
class EngineRegistry:
    """Central registry for managing TTS engines, capabilities, policies, and metrics.

    This class handles engine registration, selection based on language and requirements,
    performance tracking, and capability summaries. It uses policies for routing and
    maintains stats like success rates and durations.

    Note:
        Supports dynamic engine availability checks and fallback selection.
    """
    def __init__(self):
        self.engines: dict[str, TTSEngine] = {}
        self.capabilities: dict[str, EngineCapabilities] = {}
        self._policies: dict[str, list[str]] = {}
        self.performance_metrics: dict[str, list[float]] = {}
        self._failure_count: dict[str, int] = {}

    def register_engine(
        self,
        name: str,
        engine: TTSEngine,
        capabilities: EngineCapabilities | None = None,
    ) -> None:
        """Register a TTS engine instance with optional capabilities.

        Initializes performance tracking and failure counts for the engine.

        Args:
            name: Unique engine identifier (e.g., 'gtts', 'edge', 'piper').
            engine: The TTSEngine instance to register.
            capabilities: Optional EngineCapabilities describing features and limits.
        """
        self.engines[name] = engine
        if not hasattr(self, "_engines"):
            self._engines = {}
        self._engines[name] = engine
        if capabilities is not None:
            self.capabilities[name] = capabilities
        self.performance_metrics[name] = []
        if not hasattr(self, "failure_counts"):
            self.failure_counts = {}
        self.failure_counts[name] = 0
        self._failure_count[name] = 0

        logger.info(f"Registered engine: {name}")

    def unregister_engine(self, name: str) -> None:
        """Remove a registered engine and its associated data.

        Cleans up capabilities, metrics, and failure counts.

        Args:
            name: The engine name to unregister.
        """
        if name in self.engines:
            del self.engines[name]
            del self.capabilities[name]
            self.performance_metrics.pop(name, None)
            if hasattr(self, "failure_counts"):
                self.failure_counts.pop(name, None)
            self._failure_count.pop(name, None)
            logger.info(f"Unregistered engine: {name}")

    def set_policy(self, lang: str, engines: list[str]) -> None:
        """Configure engine priority order for a specific language.

        Args:
            lang: Language code (e.g., 'fa', 'en', 'ar').
            engines: Ordered list of engine names, first being primary.

        Note:
            Logs the policy update for monitoring.
        """
        self._policies[lang] = engines
        logger.info(f"Set policy for {lang}: {engines}")

    def get_policy(self, lang: str) -> list[str]:
        """Retrieve the engine priority policy for a language.

        Args:
            lang: Language code (e.g., 'fa').

        Returns:
            List of engine names in priority order, or empty list if no policy set.

        Note:
            For 'unknown' language, defaults to ['edge', 'gtts'] as fallback.
        """
        if lang == "unknown":
            return ["edge", "gtts"]
        return self._policies.get(lang, [])

    def get_available_engines(self) -> list[str]:
        """List all currently available (enabled and ready) engines.

        Returns:
            List of engine names that are available for use.
        """
        return [name for name, engine in self.engines.items() if engine.is_available()]

    def get_engine(self, name: str) -> TTSEngine | None:
        """Retrieve a registered engine instance by its name.

        Args:
            name: The engine's identifier.

        Returns:
            The TTSEngine instance, or None if not registered.
        """
        return self.engines.get(name)

    def get_engines_for_language(self, lang: str) -> list[str]:
        """Get available engines suitable for a given language.

        Uses policy for priority, falling back to all available if no policy.

        Args:
            lang: Language code (e.g., 'fa').

        Returns:
            List of engine names that support the language and are available.
        """
        policy = self.get_policy(lang)
        available = self.get_available_engines()
        if not policy:
            return available
        return [engine for engine in policy if engine in available]

    def select_engine(
        self, lang: str, requirements: dict[str, Any] = None
    ) -> str | None:
        """Select the optimal engine based on language and requirements.

        Iterates through policy-ordered engines and picks the first that meets all criteria.

        Args:
            lang: Language code for policy lookup.
            requirements: Dict of feature requirements (e.g., {'offline': True, 'ssml': False}).

        Returns:
            The selected engine name, or None if none match.

        Note:
            Defaults to empty requirements if None.
        """
        if requirements is None:
            requirements = {}

        available_engines = self.get_engines_for_language(lang)

        for engine_name in available_engines:
            if self.meets_requirements(engine_name, requirements):
                return engine_name

        return None

    def meets_requirements(
        self, engine_name: str, requirements: dict[str, Any]
    ) -> bool:
        """Verify if an engine satisfies given capability requirements.

        Checks features like offline, SSML, controls, language support, voice, and text length.
        Uses explicit capabilities if available, otherwise heuristics for unregistered caps.

        Args:
            engine_name: Identifier of the engine to check.
            requirements: Dict of required features (e.g., {'offline': True}).

        Returns:
            True if all requirements are met, False otherwise.
        """
        if engine_name in self.capabilities:
            capabilities = self.capabilities[engine_name]
        else:
            engine = self.engines.get(engine_name)
            if engine is None:
                return False

            class _Caps:
                offline = getattr(engine, "_offline", False)
                ssml = False
                rate_control = True
                pitch_control = True
                languages = ["en", "fa"]
                voices = ["default"]
                max_text_length = 1000

            capabilities = _Caps()

        if "offline" in requirements:
            if bool(capabilities.offline) != bool(requirements["offline"]):
                return False

        if "ssml" in requirements:
            if bool(capabilities.ssml) != bool(requirements["ssml"]):
                return False

        if "rate_control" in requirements:
            if bool(capabilities.rate_control) != bool(requirements["rate_control"]):
                return False

        if "pitch_control" in requirements:
            if bool(capabilities.pitch_control) != bool(requirements["pitch_control"]):
                return False

        if "language" in requirements:
            required_lang = requirements["language"]
            if required_lang not in capabilities.languages:
                return False

        if "voice" in requirements:
            required_voice = requirements["voice"]
            if required_voice not in capabilities.voices:
                return False

        if "text_length" in requirements:
            if requirements["text_length"] > capabilities.max_text_length:
                return False

        return True

    def record_success(self, engine_name: str, duration: float | None = None) -> None:
        """Log a successful synthesis operation for metrics tracking.

        Increments success count and appends duration if provided.
        Keeps only the last 100 durations for efficiency.

        Args:
            engine_name: The engine that succeeded.
            duration: Time taken in seconds (optional).
        """
        if not hasattr(self, "_success_count"):
            self._success_count = {}
        self._success_count[engine_name] = self._success_count.get(engine_name, 0) + 1

        if engine_name not in self.performance_metrics:
            self.performance_metrics[engine_name] = []

        if duration is not None:
            self.performance_metrics[engine_name].append(duration)

        if len(self.performance_metrics[engine_name]) > 100:
            self.performance_metrics[engine_name] = self.performance_metrics[
                engine_name
            ][-100:]

    def record_failure(self, engine_name: str) -> None:
        """Increment failure count for an engine.

        Args:
            engine_name: The engine that failed.
        """
        self._failure_count[engine_name] = self._failure_count.get(engine_name, 0) + 1

    def get_engine_stats(self, engine_name: str) -> dict[str, Any]:
        """Compute and return performance statistics for a specific engine.

        Includes averages, mins/maxes for durations, request counts, and success rate.
        Handles cases with no metrics data or only failures gracefully.

        Args:
            engine_name: The engine to get stats for.

        Returns:
            Dict with keys: avg_duration, min_duration, max_duration, total_requests, failures, successes, success_rate.
            Empty dict if no data exists.
        """
        failures = self._failure_count.get(engine_name, 0)
        successes = 0
        if hasattr(self, "_success_count"):
            successes = self._success_count.get(engine_name, 0)

        if engine_name not in self.performance_metrics:
            if failures == 0 and successes == 0:
                return {}
            return {
                "total_requests": successes,
                "failures": failures,
                "successes": successes,
                "avg_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
                "success_rate": 0.0 if (failures > 0 and successes == 0) else 1.0,
            }

        durations = self.performance_metrics[engine_name]

        if not durations:
            return {
                "avg_duration": 0.0,
                "min_duration": 0.0,
                "max_duration": 0.0,
                "total_requests": successes,
                "failures": failures,
                "successes": successes,
                "success_rate": (successes / (successes + failures))
                if (successes + failures) > 0
                else 0.0,
            }

        total = len(durations) + failures
        success_rate = (len(durations) / total) if total > 0 else 0.0
        return {
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_requests": len(durations),
            "failures": failures,
            "successes": len(durations),
            "success_rate": success_rate,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Retrieve performance statistics across all registered engines.

        Returns:
            Dict mapping engine names to their individual stats dicts.
        """
        return {
            engine_name: self.get_engine_stats(engine_name)
            for engine_name in self.engines.keys()
        }

    def reset_stats(self) -> None:
        """Clear all performance metrics, failures, and success counts."""
        for engine_name in list(self.performance_metrics.keys()):
            self.performance_metrics[engine_name] = []
        self._failure_count = {}
        if hasattr(self, "_success_count"):
            self._success_count = {}

    def get_capabilities_summary(self) -> dict[str, dict[str, Any]]:
        """Generate a summary of capabilities for all registered engines.

        Uses explicit capabilities where provided; falls back to heuristics (e.g., basic languages, controls) for others.

        Returns:
            Dict mapping engine names to capability summaries (offline, ssml, rate_control, etc.).

        Note:
            Heuristics assume common defaults like English/Farsi support and rate/pitch control.
        """
        summary: dict[str, dict[str, Any]] = {}
        for engine_name, caps in self.capabilities.items():
            summary[engine_name] = {
                "offline": getattr(caps, "offline", False),
                "ssml": getattr(caps, "ssml", False),
                "rate_control": getattr(caps, "rate_control", False),
                "pitch_control": getattr(caps, "pitch_control", False),
                "languages": getattr(caps, "languages", []),
                "voices_count": len(getattr(caps, "voices", [])),
                "max_text_length": getattr(caps, "max_text_length", 0),
            }

        for engine_name, engine in self.engines.items():
            if engine_name in summary:
                continue
            offline = getattr(engine, "_offline", False)
            summary[engine_name] = {
                "offline": offline,
                "ssml": False,
                "rate_control": True,
                "pitch_control": True,
                "languages": ["en", "fa"],
                "voices_count": 1,
                "max_text_length": 1000,
            }

        return summary
# Global singleton instance of the engine registry for easy access
registry = EngineRegistry()
