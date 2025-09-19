"""Unit tests for the EngineRegistry and EngineFactory systems in TTSKit.

This module provides comprehensive tests for registering, unregistering, and managing TTS engines,
including policy setting, availability checks, requirement matching, performance stats, and factory
operations like creating engines and retrieving info.
"""

import pytest

from ttskit.engines.base import EngineCapabilities, TTSEngine
from ttskit.engines.factory import EngineFactory
from ttskit.engines.registry import EngineRegistry

try:
    from ttskit.engines.edge_engine import EDGE_AVAILABLE
except ImportError:
    EDGE_AVAILABLE = False


class MockEngine(TTSEngine):
    """A mock TTS engine class used for testing registry functionality.

    This class simulates a basic TTSEngine implementation to test registration, capabilities,
    and other registry features without relying on real engine dependencies.

    Parameters:
    - name (str): The name of the mock engine.
    - offline (bool): Whether the engine operates offline (default: False).
    - languages (list): Supported languages (default: ["en"]).
    """

    def __init__(self, name: str, offline: bool = False, languages: list = None):
        super().__init__()
        self.name = name
        self._offline = offline
        self._languages = languages or ["en"]
        self._available = True

    def synth_to_mp3(self, text: str, lang: str = None) -> str:
        return f"/tmp/{self.name}_{text}.mp3"

    async def synth_async(
        self,
        text: str,
        lang: str = None,
        voice: str = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        return f"{self.name}_{text}".encode()

    def get_capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            offline=self._offline,
            ssml=False,
            rate_control=False,
            pitch_control=False,
            languages=self._languages,
            voices=[],
            max_text_length=1000,
        )

    def list_voices(self, lang: str = None) -> list:
        return []

    def is_available(self) -> bool:
        return self._available


class TestEngineRegistry:
    """Tests for the EngineRegistry class, which manages TTS engines and their policies.

    These tests cover engine registration/unregistration, policy management, availability checks,
    requirement matching, performance statistics recording, and capabilities summaries.
    """

    def test_register_engine(self):
        """Tests registering a new engine with the registry.

        Verifies that both the engine instance and its capabilities are stored correctly
        under the given name.

        Behavior:
        - Creates a mock engine and capabilities.
        - Registers them and asserts presence in engines and capabilities dicts.
        - Confirms the stored capabilities match the input.
        """
        registry = EngineRegistry()
        mock_engine = MockEngine("test")
        capabilities = EngineCapabilities(
            offline=True,
            ssml=False,
            rate_control=True,
            pitch_control=True,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )

        registry.register_engine("test", mock_engine, capabilities)

        assert "test" in registry.engines
        assert "test" in registry.capabilities
        assert registry.capabilities["test"] == capabilities

    def test_unregister_engine(self):
        """Tests unregistering an engine from the registry.

        Ensures that after registration, the engine and capabilities are removed
        upon unregistration.

        Behavior:
        - Registers a mock engine, confirms presence.
        - Unregisters and asserts absence from both dicts.
        """
        registry = EngineRegistry()
        mock_engine = MockEngine("test")
        capabilities = EngineCapabilities(
            offline=True,
            ssml=False,
            rate_control=True,
            pitch_control=True,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )

        registry.register_engine("test", mock_engine, capabilities)
        assert "test" in registry.engines

        registry.unregister_engine("test")
        assert "test" not in registry.engines
        assert "test" not in registry.capabilities

    def test_set_policy(self):
        """Tests setting a language-specific engine policy.

        Verifies that the policy for a given language is stored and retrievable.

        Parameters:
        - lang (str): Language code like "fa".
        - policy (list): Ordered list of engine names.

        Behavior:
        - Sets policy for "fa" to ["edge", "piper", "gtts"].
        - Retrieves and asserts it matches.
        """
        registry = EngineRegistry()
        registry.set_policy("fa", ["edge", "piper", "gtts"])

        policy = registry.get_policy("fa")
        assert policy == ["edge", "piper", "gtts"]

    def test_get_policy_default(self):
        """Tests retrieving the default policy for an unknown language.

        Ensures fallback to the default policy ["edge", "gtts"] when no specific policy exists.

        Behavior:
        - Requests policy for "unknown" lang.
        - Asserts default list is returned.
        """
        registry = EngineRegistry()
        policy = registry.get_policy("unknown")
        assert policy == ["edge", "gtts"]

    def test_get_available_engines(self):
        """Tests retrieving only available engines from the registry.

        Registers available and unavailable mocks, then checks that only available ones are returned.

        Behavior:
        - Sets _available=False for one engine.
        - Asserts only available engine name is in the result list.
        """
        registry = EngineRegistry()

        available_engine = MockEngine("available")
        capabilities = EngineCapabilities(
            offline=True,
            ssml=False,
            rate_control=True,
            pitch_control=True,
            languages=["en"],
            voices=[],
            max_text_length=1000,
        )
        registry.register_engine("available", available_engine, capabilities)

        unavailable_engine = MockEngine("unavailable")
        unavailable_engine._available = False
        registry.register_engine("unavailable", unavailable_engine, capabilities)

        available = registry.get_available_engines()
        assert "available" in available
        assert "unavailable" not in available

    def test_meets_requirements(self):
        """Tests whether an engine meets specific capability requirements.

        Covers checks for offline, SSML, rate/pitch control, language, voice, and text length.

        Behavior:
        - Sets up capabilities for "test" engine.
        - Asserts True/False for matching/non-matching requirements.
        """
        registry = EngineRegistry()
        capabilities = EngineCapabilities(
            offline=True,
            ssml=False,
            rate_control=True,
            pitch_control=True,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )
        registry.capabilities["test"] = capabilities

        assert registry.meets_requirements("test", {"offline": True})
        assert not registry.meets_requirements("test", {"offline": False})

        assert not registry.meets_requirements("test", {"ssml": True})
        assert registry.meets_requirements("test", {"ssml": False})

        assert registry.meets_requirements("test", {"rate_control": True})
        assert not registry.meets_requirements("test", {"rate_control": False})

        assert registry.meets_requirements("test", {"language": "en"})
        assert not registry.meets_requirements("test", {"language": "fa"})

        assert registry.meets_requirements("test", {"voice": "voice1"})
        assert not registry.meets_requirements("test", {"voice": "voice2"})

        assert registry.meets_requirements("test", {"text_length": 500})
        assert not registry.meets_requirements("test", {"text_length": 1500})

    def test_record_success(self):
        """Tests recording successful engine requests and updating stats.

        Records two successes with durations and verifies aggregated stats like count, average, min/max.

        Behavior:
        - Calls record_success twice.
        - Asserts total_requests=2, avg_duration=1.75, min=1.5, max=2.0.
        """
        registry = EngineRegistry()
        registry.record_success("test", 1.5)
        registry.record_success("test", 2.0)

        stats = registry.get_engine_stats("test")
        assert stats["total_requests"] == 2
        assert stats["avg_duration"] == 1.75
        assert stats["min_duration"] == 1.5
        assert stats["max_duration"] == 2.0

    def test_record_failure(self):
        """Tests recording engine failures and updating success rate.

        Records two failures and checks failure count and 0% success rate.

        Behavior:
        - Calls record_failure twice.
        - Asserts failures=2, success_rate=0.0.
        """
        registry = EngineRegistry()
        registry.record_failure("test")
        registry.record_failure("test")

        stats = registry.get_engine_stats("test")
        assert stats["failures"] == 2
        assert stats["success_rate"] == 0.0

    def test_get_engine_stats_empty(self):
        """Tests retrieving stats for a non-existent or untracked engine.

        Ensures an empty dict is returned when no stats are recorded.

        Behavior:
        - Gets stats for "nonexistent".
        - Asserts empty dict.
        """
        registry = EngineRegistry()
        stats = registry.get_engine_stats("nonexistent")
        assert stats == {}

    def test_reset_stats(self):
        """Tests resetting all engine performance statistics.

        Records some data, then resets and verifies counters are zeroed.

        Behavior:
        - Records success and failure.
        - Calls reset_stats and asserts zeroed values.
        """
        registry = EngineRegistry()
        registry.record_success("test", 1.5)
        registry.record_failure("test")

        registry.reset_stats()
        stats = registry.get_engine_stats("test")
        assert stats["total_requests"] == 0
        assert stats["failures"] == 0

    def test_get_capabilities_summary(self):
        """Tests generating a summary of all registered engine capabilities.

        Sets up a single capability and verifies key fields in the summary dict.

        Behavior:
        - Adds capabilities to registry.
        - Retrieves summary and asserts structure and values.
        """
        registry = EngineRegistry()
        capabilities = EngineCapabilities(
            offline=True,
            ssml=False,
            rate_control=True,
            pitch_control=True,
            languages=["en"],
            voices=["voice1"],
            max_text_length=1000,
        )
        registry.capabilities["test"] = capabilities

        summary = registry.get_capabilities_summary()
        assert "test" in summary
        assert summary["test"]["offline"] is True
        assert summary["test"]["ssml"] is False
        assert summary["test"]["languages"] == ["en"]


class TestEngineFactory:
    """Tests for the EngineFactory class, responsible for engine instantiation and info.

    Covers registering engine classes, creating instances, handling missing engines,
    and retrieving availability, capabilities, and detailed info for engines.
    """

    def test_register_engine_class(self):
        """Tests registering a custom engine class with the factory.

        Defines a minimal CustomEngine and capabilities dict, then verifies storage.

        Behavior:
        - Registers class and config.
        - Asserts presence in engine_classes and engine_configs.
        """
        factory = EngineFactory()

        class CustomEngine(TTSEngine):
            def synth_to_mp3(self, text: str, lang: str = None) -> str:
                return ""

            async def synth_async(
                self,
                text: str,
                lang: str = None,
                voice: str = None,
                rate: float = 1.0,
                pitch: float = 0.0,
            ) -> bytes:
                return b""

            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities(False, False, False, False, [], [], 1000)

            def list_voices(self, lang: str = None) -> list:
                return []

            def is_available(self) -> bool:
                return True

        capabilities = {
            "offline": True,
            "ssml": False,
            "rate_control": True,
            "pitch_control": False,
            "languages": ["en"],
            "voices": [],
            "max_text_length": 1000,
        }

        factory.register_engine_class("custom", CustomEngine, capabilities)
        assert "custom" in factory.engine_classes
        assert "custom" in factory.engine_configs

    def test_create_engine(self):
        """Tests creating an engine instance from the factory.

        Uses "gtts" engine with English default lang and verifies it's a TTSEngine subclass
        with the correct default language set.

        Behavior:
        - Instantiates and asserts type and property.
        """
        factory = EngineFactory()
        engine = factory.create_engine("gtts", default_lang="en")
        assert isinstance(engine, TTSEngine)
        assert engine.default_lang == "en"

    def test_create_engine_not_found(self):
        """Tests attempting to create a non-registered engine.

        Expects a ValueError with specific message when the engine name is invalid.

        Behavior:
        - Tries to create "nonexistent" engine.
        - Catches and asserts the raised ValueError.
        """
        factory = EngineFactory()
        with pytest.raises(ValueError, match="Engine 'nonexistent' not found"):
            factory.create_engine("nonexistent")

    def test_get_available_engines(self):
        """Tests listing available engines from the factory.

        Verifies known engines like "gtts" are always included, and "edge" if available.

        Behavior:
        - Retrieves list and asserts presence conditionally.
        """
        factory = EngineFactory()
        engines = factory.get_available_engines()
        assert "gtts" in engines
        if EDGE_AVAILABLE:
            assert "edge" in engines

    def test_get_engine_capabilities(self):
        """Tests retrieving capabilities for a specific engine.

        For "gtts", ensures non-None result with expected keys like "offline" and "languages".

        Returns:
        - dict: Capabilities with keys like offline, languages.
        """
        factory = EngineFactory()
        capabilities = factory.get_engine_capabilities("gtts")
        assert capabilities is not None
        assert "offline" in capabilities
        assert "languages" in capabilities

    def test_get_engine_info(self):
        """Tests getting detailed info for an engine.

        For "gtts", verifies non-None dict with name, capabilities, and class keys.

        Returns:
        - dict: Engine info including name, capabilities, class.
        """
        factory = EngineFactory()
        info = factory.get_engine_info("gtts")
        assert info is not None
        assert info["name"] == "gtts"
        assert "capabilities" in info
        assert "class" in info

    def test_get_all_engines_info(self):
        """Tests retrieving info for all registered engines.

        Ensures "gtts" is present and its info is non-None.

        Returns:
        - dict: All engine infos keyed by name.
        """
        factory = EngineFactory()
        all_info = factory.get_all_engines_info()
        assert "gtts" in all_info
        assert all_info["gtts"] is not None
