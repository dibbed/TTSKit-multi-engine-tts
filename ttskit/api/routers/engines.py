"""Handles API endpoints for text-to-speech engines and voice management.

This router provides endpoints for listing available TTS engines, their capabilities,
and managing voice options for synthesis. It acts as the main interface for clients
to discover and configure TTS capabilities before synthesis.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...engines.factory import factory as engine_factory
from ...engines.registry import registry as engine_registry
from ...public import get_engine_capabilities, get_engines

engine_factory.setup_registry(engine_registry)
from ...utils.logging_config import get_logger
from ..dependencies import OptionalAuth

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["engines"])


class EngineInfo(BaseModel):
    """Data model for TTS engine information.

    Contains all the essential details about a text-to-speech engine,
    including its capabilities, supported languages, and available voices.

    Attributes:
        name: The unique identifier of the engine (e.g., "gtts", "piper").
        available: Whether the engine is currently available for use.
        capabilities: Dictionary of engine capabilities like offline support, SSML, rate/pitch control.
        languages: List of language codes this engine can handle.
        voices: List of available voice names for this engine.
        offline: Whether this engine works without internet connection.
    """

    name: str = Field(description="Engine name")
    available: bool = Field(description="Whether engine is available")
    capabilities: dict = Field(description="Engine capabilities")
    languages: list[str] = Field(description="Supported languages")
    voices: list[str] = Field(description="Available voices")
    offline: bool = Field(description="Whether engine works offline")


class VoiceInfo(BaseModel):
    """Data model for voice information and metadata.

    Represents a specific voice within a TTS engine, including its characteristics
    and technical specifications. Used to provide clients with voice options and details.

    Attributes:
        name: The unique identifier of the voice (e.g., "fa_IR-amir-medium").
        engine: The TTS engine this voice belongs to (e.g., "piper").
        language: The language code this voice is designed for (e.g., "fa", "en").
        gender: The gender characteristics of the voice, if available (male/female).
        quality: The quality level of the voice (e.g., "low", "medium", "high").
        sample_rate: The default audio sample rate for this voice in Hz.
    """

    name: str = Field(description="Voice name")
    engine: str = Field(description="Engine name")
    language: str = Field(description="Language code")
    gender: str | None = Field(description="Voice gender")
    quality: str | None = Field(description="Voice quality")
    sample_rate: int | None = Field(description="Sample rate")


@router.get("/engines", response_model=list[EngineInfo])
async def list_engines(
    auth: OptionalAuth,
    available_only: bool = Query(
        default=False, description="Show only available engines"
    ),
):
    """Get a list of all registered TTS engines with their details.

    This endpoint provides clients with an overview of all available TTS engines,
    helping them choose appropriate engines for their synthesis needs.

    Args:
        auth: Optional authentication dependency (required for rate limiting if enabled).
        available_only: If true, only returns engines that are currently available
            for use. Defaults to false to show all registered engines.

    Returns:
        A list of EngineInfo objects, each containing the engine's name, availability
        status, capabilities (like offline support, SSML, rate control), supported
        languages, available voices, and offline capability.

    Raises:
        HTTPException: When there are internal server errors during engine retrieval.
    """
    try:
        engines = get_engines()

        if available_only:
            engines = [e for e in engines if e.get("available", False)]

        engine_infos = []
        for engine in engines:
            engine_name = engine.get("name", "unknown")
            engine_instance = engine_registry.get_engine(engine_name)

            if engine_instance:
                capabilities = engine_instance.get_capabilities()
                engine_infos.append(
                    EngineInfo(
                        name=engine_name,
                        available=engine.get("available", False),
                        capabilities={
                            "offline": capabilities.offline,
                            "ssml": capabilities.ssml,
                            "rate_control": capabilities.rate_control,
                            "pitch_control": capabilities.pitch_control,
                            "max_text_length": capabilities.max_text_length,
                        },
                        languages=capabilities.languages,
                        voices=capabilities.voices,
                        offline=capabilities.offline,
                    )
                )
            else:
                engine_infos.append(
                    EngineInfo(
                        name=engine_name,
                        available=False,
                        capabilities={},
                        languages=[],
                        voices=[],
                        offline=False,
                    )
                )

        return engine_infos

    except Exception as e:
        logger.error(f"Failed to list engines: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/engines/{engine_name}", response_model=EngineInfo)
async def get_engine_info(
    engine_name: str,
    auth: OptionalAuth,
):
    """Retrieve detailed information about a specific TTS engine.

    This endpoint allows clients to explore the full capabilities of a particular
    TTS engine, including its supported languages, available voices, and technical
    specifications before using it for synthesis.

    Args:
        engine_name: The unique identifier of the engine to retrieve information for
            (e.g., "piper", "gtts").
        auth: Optional authentication dependency (required for rate limiting if enabled).

    Returns:
        An EngineInfo object containing the engine's name, current availability status,
        detailed capabilities (offline support, SSML, rate/pitch control, max text length),
        supported language codes, available voice names, and offline capability flag.

    Raises:
        HTTPException: Returns 404 if the specified engine is not found in the registry,
            or 500 for internal server errors during capability retrieval.
    """
    try:
        engine_instance = engine_registry.get_engine(engine_name)

        if not engine_instance:
            raise HTTPException(
                status_code=404, detail=f"Engine '{engine_name}' not found"
            )

        capabilities = engine_instance.get_capabilities()

        return EngineInfo(
            name=engine_name,
            available=engine_instance.is_available(),
            capabilities={
                "offline": capabilities.offline,
                "ssml": capabilities.ssml,
                "rate_control": capabilities.rate_control,
                "pitch_control": capabilities.pitch_control,
                "max_text_length": capabilities.max_text_length,
            },
            languages=capabilities.languages,
            voices=capabilities.voices,
            offline=capabilities.offline,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get engine info for {engine_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/engines/{engine_name}/voices", response_model=list[VoiceInfo])
async def list_engine_voices(
    engine_name: str,
    auth: OptionalAuth,
    language: str | None = Query(default=None, description="Filter by language code"),
):
    """Get all available voices for a specific TTS engine.

    This endpoint helps clients discover which voices are available within
    a particular TTS engine, with optional filtering by language to narrow down
    choices before synthesis.

    Args:
        engine_name: The unique identifier of the engine whose voices to list
            (e.g., "piper", "gtts").
        auth: Optional authentication dependency (required for rate limiting if enabled).
        language: Optional language code to filter voices. If provided, only voices
            that support this language will be returned. If None, all voices are included.

    Returns:
        A list of VoiceInfo objects, each containing voice name, engine name,
        language code (extracted from voice name), gender info (if available),
        quality level, and default sample rate.

    Raises:
        HTTPException: Returns 404 if the specified engine is not found, 503 if
            the engine is not available for use, or 500 for internal server errors.
    """
    try:
        engine_instance = engine_registry.get_engine(engine_name)

        if not engine_instance:
            raise HTTPException(
                status_code=404, detail=f"Engine '{engine_name}' not found"
            )

        if not engine_instance.is_available():
            raise HTTPException(
                status_code=503, detail=f"Engine '{engine_name}' is not available"
            )

        voices = engine_instance.list_voices(language)

        # Ensure voices is a list, not a slice
        if not isinstance(voices, list):
            voices = list(voices) if voices else []

        voice_infos = []
        for voice_name in voices:
            # Extract language from voice name (e.g., "fa_IR-amir-medium" -> "fa")
            voice_lang = voice_name.split("_")[0] if "_" in voice_name else "unknown"

            voice_infos.append(
                VoiceInfo(
                    name=voice_name,
                    engine=engine_name,
                    language=voice_lang,
                    gender=None,  # Not available in current implementation
                    quality="medium",  # Default quality
                    sample_rate=22050,  # Default sample rate
                )
            )

        return voice_infos

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list voices for engine {engine_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/voices", response_model=list[VoiceInfo])
async def list_all_voices(
    auth: OptionalAuth,
    engine: str | None = Query(default=None, description="Filter by engine"),
    language: str | None = Query(default=None, description="Filter by language code"),
):
    """List all available voices across all TTS engines.

    This endpoint provides a comprehensive view of all voices available across
    all active TTS engines, with optional filtering to help clients find suitable
    voices for their synthesis needs.

    Args:
        auth: Optional authentication dependency (required for rate limiting if enabled).
        engine: Optional engine name to limit voices to a specific engine. If provided,
            only voices from this engine will be returned. If None, voices from all
            available engines are included.
        language: Optional language code to filter voices. If provided, only voices
            that support this language will be returned.

    Returns:
        A list of VoiceInfo objects representing all voices from available engines,
        each containing voice name, engine name, language code, gender, quality, and
        sample rate information.

    Raises:
        HTTPException: When there are internal server errors during voice listing.
    """
    try:
        engines = get_engines()
        available_engines = [e for e in engines if e.get("available", False)]

        if engine:
            available_engines = [
                e for e in available_engines if e.get("name") == engine
            ]

        all_voices = []
        for engine_info in available_engines:
            engine_name = engine_info.get("name")
            engine_instance = engine_registry.get_engine(engine_name)

            if engine_instance and engine_instance.is_available():
                voices = engine_instance.list_voices(language)

                for voice_name in voices:
                    voice_lang = (
                        voice_name.split("_")[0] if "_" in voice_name else "unknown"
                    )

                    all_voices.append(
                        VoiceInfo(
                            name=voice_name,
                            engine=engine_name,
                            language=voice_lang,
                            gender=None,
                            quality="medium",
                            sample_rate=22050,
                        )
                    )

        return all_voices

    except Exception as e:
        logger.error(f"Failed to list all voices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/engines/{engine_name}/test")
async def test_engine(
    engine_name: str,
    auth: OptionalAuth,
    text: str = Query(default="Hello, world!", description="Test text"),
    language: str = Query(default="en", description="Language code"),
):
    """Perform a quick functionality test on a specific TTS engine.

    This diagnostic endpoint tests whether a particular TTS engine is working
    correctly by attempting to synthesize a short text sample. It helps verify
    engine configuration and availability without requiring full synthesis workflows.

    Args:
        engine_name: The unique identifier of the engine to test
            (e.g., "piper", "gtts").
        auth: Optional authentication dependency (required for rate limiting if enabled).
        text: The text sample to use for testing. Defaults to "Hello, world!"
            to provide consistent, brief testing.
        language: The language code for the test. Defaults to "en" for English.

    Returns:
        A dictionary containing:
        - success: Boolean indicating if the test was successful
        - engine: The engine name that was tested
        - test_text: The original text used for testing
        - language: The language code used
        - duration: Audio duration in seconds
        - size: Audio file size in bytes
        - format: Audio format (e.g., "wav")
        - message: Human-readable status message

    Raises:
        HTTPException: Returns 404 if the engine is not found, 503 if the engine
            is unavailable, or 500 for synthesis failures and internal errors.
    """
    try:
        engine_instance = engine_registry.get_engine(engine_name)

        if not engine_instance:
            raise HTTPException(
                status_code=404, detail=f"Engine '{engine_name}' not found"
            )

        if not engine_instance.is_available():
            raise HTTPException(
                status_code=503, detail=f"Engine '{engine_name}' is not available"
            )

        # Test synthesis
        from ...public import SynthConfig

        config = SynthConfig(
            text=text,
            lang=language,
            engine=engine_name,
            output_format="wav",
            cache=False,
        )

        from ...public import TTS

        tts = TTS(default_lang=language)

        result = tts.synth_async(config)
        import asyncio as _asyncio

        if _asyncio.iscoroutine(result) or hasattr(result, "__await__"):
            audio_out = await result
        else:
            audio_out = result

        return {
            "success": True,
            "engine": engine_name,
            "test_text": text,
            "language": language,
            "duration": audio_out.duration,
            "size": audio_out.size,
            "format": audio_out.format,
            "message": f"Engine '{engine_name}' is working correctly",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test engine {engine_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/capabilities")
async def get_all_capabilities(
    auth: OptionalAuth,
):
    """Retrieve comprehensive capabilities information for all TTS engines.

    This endpoint provides an aggregated view of all engine capabilities,
    helping clients understand the full range of synthesis features available
    across the system for planning their TTS workflows.

    Args:
        auth: Optional authentication dependency (required for rate limiting if enabled).

    Returns:
        A dictionary containing detailed capabilities information for all engines,
        including supported languages, voices, offline capabilities, SSML support,
        rate control, pitch control, and maximum text length limits.

    Raises:
        HTTPException: When there are internal server errors during capability retrieval.
    """
    try:
        capabilities = get_engine_capabilities()
        return capabilities

    except Exception as e:
        logger.error(f"Failed to get engine capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
