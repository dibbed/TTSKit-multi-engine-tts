"""Tests for engine registry."""

from ttskit.engines.base import EngineCapabilities, TTSEngine
from ttskit.engines.registry import EngineRegistry


class MockEngine(TTSEngine):
    """Mock engine for testing."""

    def __init__(self, name: str, offline: bool = False):
        super().__init__()
        self.name = name
        self._offline = offline
        self._available = True

    def synth_to_mp3(self, text: str, lang: str = None) -> str:
        return f"/tmp/{self.name}.mp3"

    async def synth_async(
        self,
        text: str,
        lang: str = None,
        voice: str = None,
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        return b"fake audio"

    def synth(self, text: str, lang: str, voice: str, rate: str, pitch: str) -> bytes:
        return b"fake audio"

    def get_capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            offline=self._offline,
            ssml=False,
            rate=True,
            pitch=True,
            languages=["en", "fa"],
            voices=["default"],
            max_text_length=1000,
        )

    def list_voices(self, lang: str = None) -> list:
        return ["default"]

    def is_available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        self._available = available


class TestEngineRegistry:
    """Test cases for EngineRegistry."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = EngineRegistry()
        assert registry is not None

    def test_register_engine(self):
        """Test engine registration."""
        registry = EngineRegistry()
        engine = MockEngine("test_engine")

        registry.register_engine("test_engine", engine)

        assert "test_engine" in registry._engines
        assert registry._engines["test_engine"] == engine

    def test_set_policy(self):
        """Test policy setting."""
        registry = EngineRegistry()

        registry.set_policy("en", ["engine1", "engine2"])

        assert registry._policies["en"] == ["engine1", "engine2"]

    def test_get_policy(self):
        """Test policy retrieval."""
        registry = EngineRegistry()

        registry.set_policy("en", ["engine1", "engine2"])

        policy = registry.get_policy("en")
        assert policy == ["engine1", "engine2"]

        policy = registry.get_policy("fa")
        assert policy == []

    def test_get_available_engines(self):
        """Test getting available engines."""
        registry = EngineRegistry()

        engine1 = MockEngine("engine1")
        engine2 = MockEngine("engine2")
        engine2.set_available(False)

        registry.register_engine("engine1", engine1)
        registry.register_engine("engine2", engine2)

        available = registry.get_available_engines()
        assert "engine1" in available
        assert "engine2" not in available

    def test_meets_requirements(self):
        """Test requirement checking."""
        registry = EngineRegistry()

        engine = MockEngine("test_engine", offline=True)
        registry.register_engine("test_engine", engine)

        assert registry.meets_requirements("test_engine", {"offline": True})
        assert not registry.meets_requirements("test_engine", {"offline": False})
        assert not registry.meets_requirements("nonexistent", {"offline": True})

    def test_record_success(self):
        """Test success recording."""
        registry = EngineRegistry()

        registry.record_success("test_engine")

        assert registry._success_count["test_engine"] == 1

        registry.record_success("test_engine")
        assert registry._success_count["test_engine"] == 2

    def test_record_failure(self):
        """Test failure recording."""
        registry = EngineRegistry()

        registry.record_failure("test_engine")

        assert registry._failure_count["test_engine"] == 1

        registry.record_failure("test_engine")
        assert registry._failure_count["test_engine"] == 2

    def test_get_engine_stats(self):
        """Test engine statistics."""
        registry = EngineRegistry()

        registry.record_success("test_engine")
        registry.record_success("test_engine")
        registry.record_failure("test_engine")

        stats = registry.get_engine_stats("test_engine")

        assert stats["successes"] == 2
        assert stats["failures"] == 1
        assert stats["success_rate"] == 2 / 3

    def test_reset_stats(self):
        """Test statistics reset."""
        registry = EngineRegistry()

        registry.record_success("test_engine")
        registry.record_failure("test_engine")

        registry.reset_stats()

        assert registry._success_count == {}
        assert registry._failure_count == {}

    def test_get_capabilities_summary(self):
        """Test capabilities summary."""
        registry = EngineRegistry()

        engine = MockEngine("test_engine", offline=True)
        registry.register_engine("test_engine", engine)

        summary = registry.get_capabilities_summary()

        assert "test_engine" in summary
        assert summary["test_engine"]["offline"] is True
        assert summary["test_engine"]["ssml"] is False
