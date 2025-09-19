"""Manages API endpoints for text-to-speech synthesis and batch processing.

This router handles the core synthesis functionality, providing endpoints
for converting text to audio files, processing multiple texts in batches,
and previewing synthesis parameters before final audio generation.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...config import settings
from ...public import TTS, SynthConfig
from ...utils.logging_config import get_logger
from ...utils.text import clean_text, get_text_length, normalize_text, remove_emojis
from ...utils.validate import validate_language_code, validate_user_input
from ..dependencies import OptionalAuth, RateLimit

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["synthesis"])

tts: TTS | None = None


class SynthRequest(BaseModel):
    """Data model for text-to-speech synthesis requests.

    This model defines the parameters needed to perform a single text synthesis
    operation. It provides complete control over synthesis settings including
    language, voice, audio format, and speech characteristics.

    Attributes:
        text: The text content to be converted to speech. Must be 1-5000 characters long.
        lang: Language code for the synthesis (e.g., 'en' for English, 'fa' for Farsi, 'ar' for Arabic).
        voice: Optional specific voice name to use. If None, the engine's default voice is selected.
        engine: Optional TTS engine to use. If None, the system auto-selects the best engine.
        rate: Speech rate multiplier (0.1-3.0). 1.0 is normal speed, lower is slower, higher is faster.
        pitch: Pitch adjustment in semitones (-12 to +12). 0.0 is default pitch, negative lowers, positive raises.
        format: Output audio format. Supported: 'ogg', 'mp3', 'wav'. Defaults to 'ogg'.

    Example:
        SynthRequest(
            text="Hello, how are you today?",
            lang="en",
            voice="alice-medium",
            engine="piper",
            rate=1.2,
            pitch=2.0,
            format="mp3"
        )
    """

    text: str = Field(
        ..., description="Text to synthesize", min_length=1, max_length=5000
    )
    lang: str = Field(
        default="en", description="Language code (e.g., 'en', 'fa', 'ar')"
    )
    voice: str | None = Field(default=None, description="Voice name (engine-specific)")
    engine: str | None = Field(default=None, description="TTS engine to use")
    rate: float = Field(
        default=1.0, ge=0.1, le=3.0, description="Speech rate multiplier"
    )
    pitch: float = Field(
        default=0.0, ge=-12.0, le=12.0, description="Pitch adjustment in semitones"
    )
    format: str = Field(
        default="ogg", pattern="^(ogg|mp3|wav)$", description="Output audio format"
    )


class BatchSynthRequest(BaseModel):
    """Data model for batch text-to-speech synthesis requests.

    This model defines parameters for processing multiple texts in a single request.
    It applies consistent settings across all texts for efficient bulk processing,
    making it ideal for scenarios like processing lists, documents, or user data.

    Attributes:
        texts: List of text strings to synthesize audio for. Must contain 1-10 texts.
            Each text has maxlength constraints applied during processing.
        lang: Language code applied to all texts (e.g., 'en' for English, 'fa' for Farsi, 'ar' for Arabic).
        voice: Optional specific voice name to use for all texts. If None, default voices are selected.
        engine: Optional TTS engine to use for all texts. If None, the system auto-selects engines.
        rate: Speech rate multiplier applied to all texts (0.1-3.0). 1.0 is normal speed.
        pitch: Pitch adjustment applied to all texts, in semitones (-12 to +12). 0.0 is default pitch.
        format: Output audio format applied to all texts. Supported: 'ogg', 'mp3', 'wav'. Defaults to 'ogg'.

    Notes:
        - All text validation and length limits are applied individually to each text.
        - Failed texts don't stop processing of successful ones.
        - Individual text failures are reported without affecting the overall success status.
        - The returned response includes both successful and failed text results for transparency.

    Example:
        BatchSynthRequest(
            texts=["Hello world", "How are you?", "Thank you!"],
            lang="en",
            voice="alice-medium",
            engine="piper",
            rate=1.1,
            pitch=0.0,
            format="mp3"
        )
    """

    texts: list[str] = Field(
        ..., description="List of texts to synthesize", min_length=1, max_length=10
    )
    lang: str = Field(
        default="en", description="Language code (e.g., 'en', 'fa', 'ar')"
    )
    voice: str | None = Field(default=None, description="Voice name (engine-specific)")
    engine: str | None = Field(default=None, description="TTS engine to use")
    rate: float = Field(
        default=1.0, ge=0.1, le=3.0, description="Speech rate multiplier"
    )
    pitch: float = Field(
        default=0.0, ge=-12.0, le=12.0, description="Pitch adjustment in semitones"
    )
    format: str = Field(
        default="ogg", pattern="^(ogg|mp3|wav)$", description="Output audio format"
    )


class SynthResponse(BaseModel):
    """Data model for text-to-speech synthesis responses.

    This model represents the result of a synthesis operation, providing metadata
    about the generated audio and the parameters used in its creation.

    Attributes:
        success: Whether the synthesis operation completed successfully.
        duration: Length of the generated audio in seconds (floating point precision).
        size: Size of the audio file in bytes.
        format: Audio format of the generated file (e.g., "ogg", "mp3", "wav").
        engine: Name of the TTS engine used for synthesis (e.g., "piper", "gtts").
        voice: Name of the voice used, or None if default was applied.
        cached: Whether this response came from the cache instead of fresh synthesis.

    Notes:
        This model is used internally by the API and is not directly returned to clients.
        For streaming responses, only the audio data with metadata headers is returned.
    """

    success: bool = Field(description="Whether synthesis was successful")
    duration: float = Field(description="Audio duration in seconds")
    size: int = Field(description="Audio file size in bytes")
    format: str = Field(description="Audio format")
    engine: str = Field(description="Engine used for synthesis")
    voice: str | None = Field(description="Voice used for synthesis")
    cached: bool = Field(description="Whether result was from cache")


def init_tts():
    """Initialize the global TTS instance for synthesis operations.

    Creates a singleton TTS instance if one doesn't already exist, using the
    default language from application settings. This ensures consistent behavior
    across multiple synthesis requests within the same API instance.

    Notes:
        This function is thread-safe for the global variable assignment.
        The TTS instance is reused for all subsequent synthesis operations
        to improve performance and maintain consistency.
    """
    global tts
    if tts is None:
        tts = TTS(default_lang=settings.default_lang)


@router.post("/synth", response_class=StreamingResponse)
async def synth_audio(
    request: SynthRequest,
    auth: OptionalAuth,
    rate_limit: RateLimit,
    http_request: Request,
):
    """Synthesize text into audio and return it as a streaming response.

    This endpoint performs the core text-to-speech conversion, transforming input text
    into audio data using the configured TTS engine. It handles text preparation,
    synthesis configuration, and returns the audio as a streaming HTTP response
    for efficient delivery of potentially large audio files.

    Args:
        request: SynthRequest object containing text and synthesis parameters.
        auth: Optional authentication dependency (required for rate limiting if enabled).
        rate_limit: Rate limiting dependency to control request frequency.
        http_request: FastAPI Request object for accessing request metadata.

    Returns:
        StreamingResponse: Audio file as a streaming HTTP response with appropriate
        content-type headers and metadata in response headers.

    Raises:
        HTTPException: Returns 400 for validation errors (invalid language, text too long),
            429 for rate limiting violations, or 500 for synthesis failures.

    Notes:
        - Text is automatically cleaned and processed (emoji removal, normalization).
        - Synthesis results are cached for improved performance on repeated requests.
        - Audio format affects quality, file size, and browser compatibility.
        - Rate limiting is handled at the dependency level before synthesis begins.
    """
    init_tts()

    try:
        # Validate input
        validate_language_code(request.lang)
        validate_user_input(request.text, request.lang)

        # Clean and normalize text
        cleaned_text = clean_text(request.text)
        normalized_text = normalize_text(cleaned_text)
        emojis_removed = remove_emojis(normalized_text)

        # Check text length
        text_length = get_text_length(emojis_removed)
        if text_length > settings.max_chars:
            raise HTTPException(
                status_code=400,
                detail=f"Text too long: {text_length} characters (max: {settings.max_chars})",
                headers={
                    "X-Error-Type": "text_too_long",
                    "X-Text-Length": str(text_length),
                    "X-Max-Length": str(settings.max_chars),
                },
            )

        # Create synthesis config
        config = SynthConfig(
            text=emojis_removed,
            lang=request.lang,
            voice=request.voice,
            engine=request.engine,
            rate=request.rate,
            pitch=request.pitch,
            output_format=request.format,
            cache=True,
        )

        # Synthesize audio
        try:
            result = tts.synth_async(config)
            import asyncio as _asyncio

            if _asyncio.iscoroutine(result) or hasattr(result, "__await__"):
                audio_out = await result
            else:
                audio_out = result
        except Exception as synth_error:
            logger.error(f"Synthesis error: {synth_error}")
            raise HTTPException(
                status_code=500, detail=f"Synthesis failed: {str(synth_error)}"
            ) from synth_error

        # Determine content type
        content_type_map = {
            "ogg": "audio/ogg",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
        }
        content_type = content_type_map.get(request.format, "audio/ogg")

        # Create streaming response
        def generate_audio():
            yield audio_out.data

        # Log successful synthesis
        logger.info(
            f"Synthesis successful: '{request.text[:50]}...' "
            f"({request.lang}, {request.engine or 'auto'}, {request.format}) "
            f"Duration: {audio_out.duration:.2f}s, Size: {audio_out.size} bytes"
        )

        return StreamingResponse(
            generate_audio(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=synthesis.{request.format}",
                "X-Audio-Duration": str(audio_out.duration),
                "X-Audio-Size": str(audio_out.size),
                "X-Engine-Used": audio_out.engine or "auto",
                "X-Voice-Used": request.voice or "auto",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/synth/batch")
async def batch_synth_audio(
    request: BatchSynthRequest,
    auth: OptionalAuth,
    rate_limit: RateLimit,
):
    """Process multiple texts into audio files in a single request.

    This endpoint enables efficient bulk text-to-speech processing, synthesizing
    a list of texts into audio files. Each text is processed individually, but
    failures in one text don't prevent successful processing of others. The
    response includes detailed results for each text item with error handling.

    Args:
        request: BatchSynthRequest containing the list of texts and shared synthesis parameters.
        auth: Optional authentication dependency (required for rate limiting if enabled).
        rate_limit: Rate limiting dependency to control batch request frequency.

    Returns:
        Dictionary containing batch processing results with the following keys:
        - success: Boolean indicating overall batch status
        - total_texts: Total number of texts submitted for processing
        - successful: Number of texts processed successfully
        - failed: Number of texts that failed processing
        - results: List of dictionaries for each text, containing index, status, audio data, and metadata

    Raises:
        HTTPException: Returns 400 for invalid request format, 429 for rate limiting,
            or 500 for internal processing errors.

    Notes:
        - Each text item is processed independently with its own validation and error handling.
        - Results are returned in the same order as the input texts array.
        - Base64 encoding enables safe transport of binary audio data in JSON responses.
        - This endpoint is ideal for processing multiple related texts (e.g., lists, articles).
    """
    init_tts()

    try:
        results = []

        for i, text in enumerate(request.texts):
            try:
                # Validate input
                validate_language_code(request.lang)
                validate_user_input(text, request.lang)

                # Clean and normalize text
                cleaned_text = clean_text(text)
                normalized_text = normalize_text(cleaned_text)
                emojis_removed = remove_emojis(normalized_text)

                # Check text length
                text_length = get_text_length(emojis_removed)
                if text_length > settings.max_chars:
                    results.append(
                        {
                            "index": i,
                            "success": False,
                            "error": f"Text too long: {text_length} characters (max: {settings.max_chars})",
                        }
                    )
                    continue

                # Create synthesis config
                config = SynthConfig(
                    text=emojis_removed,
                    lang=request.lang,
                    voice=request.voice,
                    engine=request.engine,
                    rate=request.rate,
                    pitch=request.pitch,
                    output_format=request.format,
                    cache=True,
                )

                # Synthesize audio
                result = tts.synth_async(config)
                import asyncio as _asyncio

                if _asyncio.iscoroutine(result) or hasattr(result, "__await__"):
                    audio_out = await result
                else:
                    audio_out = result

                # Convert to base64
                import base64

                audio_base64 = base64.b64encode(audio_out.data).decode("utf-8")

                results.append(
                    {
                        "index": i,
                        "success": True,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "audio_base64": audio_base64,
                        "duration": audio_out.duration,
                        "size": audio_out.size,
                        "format": audio_out.format,
                        "engine": audio_out.engine or "auto",
                        "voice": request.voice or "auto",
                    }
                )

            except Exception as e:
                logger.error(f"Batch synthesis error for text {i}: {e}")
                results.append({"index": i, "success": False, "error": str(e)})

        return {
            "success": True,
            "total_texts": len(request.texts),
            "successful": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Batch synthesis endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/synth/preview")
async def preview_synthesis(
    auth: OptionalAuth,
    rate_limit: RateLimit,
    text: str = Query(..., description="Text to preview"),
    lang: str = Query(default="en", description="Language code"),
    engine: str = Query(default=None, description="TTS engine to use"),
    voice: str = Query(default=None, description="Voice name"),
):
    """Preview synthesis parameters without generating the actual audio file.

    This endpoint validates text and synthesis parameters, then returns metadata
    and estimates without actually generating audio. It's useful for checking
    text length, estimating processing time, and validating parameters before
    committing to full synthesis.

    Args:
        auth: Optional authentication dependency (required for rate limiting if enabled).
        rate_limit: Rate limiting dependency to control preview request frequency.
        text: The text content to analyze and preview. Required for validation.
        lang: Language code for the preview. Defaults to "en" for English.
        engine: Optional engine name to validate availability. If specified but
            unavailable, the request will fail before processing.
        voice: Optional voice name for preview. Used for validation purposes.

    Returns:
        Dictionary containing preview information with the following keys:
        - success: Boolean indicating if preview completed successfully
        - text_preview: Truncated version of the processed text (max 100 chars)
        - text_length: Character count of the processed text
        - language: Confirmed language code after validation
        - engine: Engine name that would be used ("auto" if not specified)
        - voice: Voice name that would be used ("auto" if not specified)
        - estimated_duration: Rough duration estimate in seconds
        - available_engines: List of currently available engine names

    Raises:
        HTTPException: Returns 400 for validation errors (invalid language, text too long,
            unavailable engine), 429 for rate limiting, or 500 for internal processing errors.

    Notes:
        - This endpoint has the same validation and text processing as actual synthesis.
        - Estimated duration is approximate (~100ms per character) and should be used as a guide only.
        - Use this endpoint to validate requests before committing to expensive synthesis operations.
    """
    init_tts()

    try:
        # Validate input
        validate_language_code(lang)
        validate_user_input(text, lang)

        # Clean and normalize text
        cleaned_text = clean_text(text)
        normalized_text = normalize_text(cleaned_text)
        emojis_removed = remove_emojis(normalized_text)

        # Check text length
        text_length = get_text_length(emojis_removed)
        if text_length > settings.max_chars:
            raise HTTPException(
                status_code=400,
                detail=f"Text too long: {text_length} characters (max: {settings.max_chars})",
            )

        # Get engine info
        from ...engines.registry import registry as engine_registry

        available_engines = engine_registry.get_available_engines()

        if engine and engine not in available_engines:
            raise HTTPException(
                status_code=400,
                detail=f"Engine '{engine}' not available. Available engines: {available_engines}",
            )

        # Estimate duration (rough calculation)
        estimated_duration = text_length * 0.1  # ~100ms per character

        return {
            "success": True,
            "text_preview": emojis_removed[:100] + "..."
            if len(emojis_removed) > 100
            else emojis_removed,
            "text_length": text_length,
            "language": lang,
            "engine": engine or "auto",
            "voice": voice or "auto",
            "estimated_duration": estimated_duration,
            "available_engines": available_engines,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
