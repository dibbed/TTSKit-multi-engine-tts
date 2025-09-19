"""Audio processing subsystem for TTSKit.

This module provides the core audio processing functionality for TTSKit, exposing
the AudioPipeline class for advanced audio manipulation, enhancement, and conversion.
The global pipeline instance enables convenient access to audio processing features
throughout the TTSKit ecosystem. Supports various audio formats and effects with
graceful degradation when optional dependencies are missing.

Main components:
- AudioPipeline: Core audio processing class with extensive capabilities
- pipeline: Global singleton instance for easy access
"""

from .pipeline import AudioPipeline, pipeline

__all__ = ["AudioPipeline", "pipeline"]
