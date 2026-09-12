"""Engine health and diagnostic probes for TTSKit.

Provides active synthesis probes to test whether TTS engines (Edge, Piper, gTTS)
are operational, measuring latency, bytes produced, and configuration issues.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from ..utils.logging_config import get_logger
from .registry import registry as engine_registry

logger = get_logger(__name__)


@dataclass
class EngineProbeResult:
    """Result of probing a TTS engine."""

    engine: str
    available: bool
    status: str  # "ok", "error", "not_configured", "unavailable"
    latency_ms: float = 0.0
    bytes_produced: int = 0
    message: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "available": self.available,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "bytes_produced": self.bytes_produced,
            "message": self.message,
            "error": self.error,
        }


async def probe_engine(
    engine_name: str,
    timeout_seconds: float = 5.0,
    test_text: str = "Test synthesis",
) -> EngineProbeResult:
    """Probe a single TTS engine with real synthesis.

    Args:
        engine_name: The name of the engine (e.g., 'edge', 'piper', 'gtts').
        timeout_seconds: Maximum duration before probe times out.
        test_text: Short text string for synthesis check.

    Returns:
        EngineProbeResult with latency, status, and diagnostic message.
    """
    normalized = engine_name.lower().strip()
    engine = engine_registry.get_engine(normalized)

    if engine is None:
        try:
            from .factory import create_engine

            engine = create_engine(normalized)
        except Exception as e:
            return EngineProbeResult(
                engine=normalized,
                available=False,
                status="not_configured",
                message=f"Engine not registered or install missing: {e}",
                error=str(e),
            )

    if not engine.is_available():
        return EngineProbeResult(
            engine=normalized,
            available=False,
            status="unavailable",
            message=f"{normalized.capitalize()} is unavailable (missing models, dependencies, or offline)",
        )

    capabilities = engine.get_capabilities()
    test_lang = "en"
    if capabilities.languages:
        if "en" in capabilities.languages:
            test_lang = "en"
        elif "fa" in capabilities.languages:
            test_lang = "fa"
        else:
            test_lang = capabilities.languages[0]

    start_time = time.perf_counter()
    try:
        if hasattr(engine, "synth_async"):
            synth_coro = engine.synth_async(test_text, lang=test_lang)
            audio_bytes = await asyncio.wait_for(synth_coro, timeout=timeout_seconds)
        else:
            loop = asyncio.get_running_loop()
            audio_bytes = await asyncio.wait_for(
                loop.run_in_executor(None, engine.synth, test_text, test_lang),
                timeout=timeout_seconds,
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if audio_bytes and len(audio_bytes) > 0:
            return EngineProbeResult(
                engine=normalized,
                available=True,
                status="ok",
                latency_ms=round(latency_ms, 2),
                bytes_produced=len(audio_bytes),
                message=f"OK ({len(audio_bytes)} bytes in {latency_ms:.0f}ms)",
            )
        else:
            return EngineProbeResult(
                engine=normalized,
                available=False,
                status="error",
                latency_ms=round(latency_ms, 2),
                bytes_produced=0,
                message="Synthesis returned empty audio data",
                error="empty_data",
            )
    except TimeoutError:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return EngineProbeResult(
            engine=normalized,
            available=False,
            status="error",
            latency_ms=round(latency_ms, 2),
            message=f"Probe timed out after {timeout_seconds}s",
            error="timeout",
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        logger.warning(f"Engine probe failed for {normalized}: {e}")
        return EngineProbeResult(
            engine=normalized,
            available=False,
            status="error",
            latency_ms=round(latency_ms, 2),
            message=f"Error: {e}",
            error=str(e),
        )


async def probe_all_engines(
    engines: list[str] | None = None,
    timeout_seconds: float = 5.0,
) -> list[EngineProbeResult]:
    """Probe all configured or specified TTS engines."""
    if engines is None:
        registered = list(engine_registry.engines.keys())
        engines = registered if registered else ["edge", "piper", "gtts"]

    results = []
    for eng in engines:
        result = await probe_engine(eng, timeout_seconds=timeout_seconds)
        results.append(result)
    return results
