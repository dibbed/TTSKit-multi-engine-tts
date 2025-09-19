#!/usr/bin/env python3
"""FastAPI REST API example for TTSKit.

This example demonstrates how to create a REST API using TTSKit with FastAPI.
"""

import atexit
import os
import shutil
import tempfile
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ttskit import TTS, SynthConfig, get_engines, list_voices
from ttskit.config import settings
from ttskit.exceptions import (
    AllEnginesFailedError,
    AudioConversionError,
    EngineNotFoundError,
    TextValidationError,
    TTSError,
)


def cleanup_temp_files():
    """Cleans up temporary files created during TTSKit execution.

    Removes all temporary files and directories matching the ttskit pattern
    from the system temp directory. Ignores cleanup errors gracefully.
    """
    try:
        temp_dir = tempfile.gettempdir()
        ttskit_temp_pattern = f"{temp_dir}/ttskit_*"

        import glob

        temp_files = glob.glob(ttskit_temp_pattern)
        for temp_file in temp_files:
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                elif os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
            except Exception:
                pass

        print("🧹 Cleaned up temporary files")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


atexit.register(cleanup_temp_files)


class SynthesisRequest(BaseModel):
    """Pydantic model for text-to-speech synthesis requests.

    Validates input parameters including text content, language, engine selection,
    voice settings, speech rate, pitch adjustment, and output format.
    """

    text: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_text_length,
        description="Text to synthesize",
    )
    lang: str = Field(default=settings.default_lang, description="Language code")
    engine: Optional[str] = Field(default=None, description="TTS engine to use")
    voice: Optional[str] = Field(default=None, description="Voice name")
    rate: float = Field(
        default=1.0, ge=0.1, le=3.0, description="Speech rate multiplier"
    )
    pitch: float = Field(
        default=0.0, ge=-12.0, le=12.0, description="Pitch adjustment in semitones"
    )
    output_format: str = Field(default="ogg", description="Output audio format")

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v):
        """Validates that text is not empty or only whitespace.

        Args:
            v: Text value to validate

        Returns:
            Stripped text value

        Raises:
            ValueError: If text is empty or only whitespace
        """
        if not v.strip():
            raise ValueError("Text cannot be empty or only whitespace")
        return v.strip()

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v):
        """Validates that output format is supported.

        Args:
            v: Output format to validate

        Returns:
            Lowercase format string

        Raises:
            ValueError: If format is not in allowed list
        """
        allowed_formats = ["ogg", "mp3", "wav"]
        if v.lower() not in allowed_formats:
            raise ValueError(f"Output format must be one of: {allowed_formats}")
        return v.lower()


class BatchSynthesisRequest(BaseModel):
    """Pydantic model for batch synthesis requests.

    Contains a list of individual synthesis requests for processing multiple
    texts in a single API call. Limited to 100 requests per batch.
    """

    requests: List[SynthesisRequest] = Field(
        ..., min_items=1, max_items=100, description="List of synthesis requests"
    )


class SynthesisResponse(BaseModel):
    """Pydantic model for synthesis operation results.

    Contains success status, audio metadata (duration, size, format),
    engine information, and error details if synthesis failed.
    """

    success: bool = Field(description="Whether synthesis was successful")
    duration: Optional[float] = Field(
        default=None, description="Audio duration in seconds"
    )
    size: Optional[int] = Field(default=None, description="Audio size in bytes")
    format: Optional[str] = Field(default=None, description="Audio format")
    engine_used: Optional[str] = Field(
        default=None, description="Engine used for synthesis"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BatchSynthesisResponse(BaseModel):
    """Pydantic model for batch synthesis operation results.

    Contains individual synthesis results, total request count, and summary
    statistics for successful and failed operations.
    """

    results: List[SynthesisResponse] = Field(description="List of synthesis results")
    total: int = Field(description="Total number of requests")
    successful: int = Field(description="Number of successful requests")
    failed: int = Field(description="Number of failed requests")


def create_simple_api() -> FastAPI:
    """Creates a FastAPI application with TTSKit integration.

    Sets up endpoints for synthesis, voice listing, engine information,
    health checks, and system info. Returns configured FastAPI instance.
    """
    app = FastAPI(
        title="TTSKit Simple API",
        description="A simple REST API for text-to-speech synthesis",
        version="1.0.0",
    )

    tts = TTS(default_lang=settings.default_lang)

    @app.get("/")
    async def root():
        """Provides API information and available endpoints.

        Returns:
            Dictionary with service info, endpoints, and usage examples
        """
        return {
            "service": "TTSKit Simple API",
            "version": "1.0.0",
            "status": "running",
            "description": "A simple REST API for text-to-speech synthesis",
            "endpoints": {
                "synthesize": "/synthesize",
                "voices": "/voices",
                "engines": "/engines",
                "health": "/health",
                "info": "/info",
                "docs": "/docs",
                "openapi": "/openapi.json",
            },
            "usage": {
                "synthesis": "POST /synthesize with JSON body",
                "batch": "POST /batch with array of requests",
                "documentation": "Visit /docs for interactive API documentation",
            },
        }

    @app.post("/synthesize", response_class=StreamingResponse)
    async def synthesize(request: SynthesisRequest):
        """Synthesizes text to speech and returns audio as streaming response.

        Args:
            request: Synthesis request with text, language, voice, and format options

        Returns:
            StreamingResponse containing audio data with appropriate headers

        Raises:
            HTTPException: For various synthesis errors with appropriate status codes
        """
        try:
            config = SynthConfig(
                text=request.text,
                lang=request.lang,
                voice=request.voice,
                engine=request.engine,
                rate=request.rate,
                pitch=request.pitch,
                output_format=request.output_format,
                cache=True,
            )

            audio_out = await tts.synth_async(config)

            content_type_map = {
                "ogg": "audio/ogg",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
            }
            content_type = content_type_map.get(request.output_format, "audio/ogg")

            def generate_audio():
                yield audio_out.data

            return StreamingResponse(
                generate_audio(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=synthesis.{request.output_format}",
                    "X-Audio-Duration": str(audio_out.duration),
                    "X-Audio-Size": str(audio_out.size),
                    "X-Engine-Used": request.engine or "auto",
                    "X-Cache-Status": "hit"
                    if hasattr(audio_out, "cached") and audio_out.cached
                    else "miss",
                },
            )

        except TextValidationError as e:
            raise HTTPException(
                status_code=400, detail=f"Text validation failed: {str(e)}"
            )
        except EngineNotFoundError as e:
            raise HTTPException(status_code=404, detail=f"Engine not found: {str(e)}")
        except AudioConversionError as e:
            raise HTTPException(
                status_code=422, detail=f"Audio conversion failed: {str(e)}"
            )
        except AllEnginesFailedError as e:
            raise HTTPException(status_code=503, detail=f"All engines failed: {str(e)}")
        except TTSError as e:
            raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    @app.get("/voices")
    async def get_voices(
        lang: Optional[str] = Query(None, description="Filter by language"),
        engine: Optional[str] = Query(None, description="Filter by engine"),
    ):
        """Retrieves available voices with optional filtering.

        Args:
            lang: Optional language code to filter voices
            engine: Optional engine name to filter voices

        Returns:
            Dictionary with voices list, count, and applied filters

        Raises:
            HTTPException: If voice retrieval fails
        """
        try:
            voices = list_voices(lang=lang, engine=engine)
            return {
                "voices": voices,
                "count": len(voices),
                "filters": {"language": lang, "engine": engine},
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get voices: {str(e)}"
            ) from e

    @app.get("/engines")
    async def get_engines_info():
        """Retrieves information about all available TTS engines.

        Returns:
            Dictionary with engines list, counts, and availability summary

        Raises:
            HTTPException: If engine information retrieval fails
        """
        try:
            engines = get_engines()
            available_engines = [e for e in engines if e.get("available", False)]
            return {
                "engines": engines,
                "count": len(engines),
                "available_count": len(available_engines),
                "summary": {
                    "total": len(engines),
                    "available": len(available_engines),
                    "unavailable": len(engines) - len(available_engines),
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get engines: {str(e)}"
            ) from e

    @app.get("/health")
    async def health():
        """Provides health status of the TTS service.

        Checks engine availability and returns service health status.
        Service is considered healthy if at least one engine is available.

        Returns:
            Dictionary with health status, engine counts, and timestamp
        """
        try:
            engines = get_engines()
            available_engines = [e for e in engines if e.get("available", False)]

            is_healthy = len(available_engines) > 0

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "engines_available": len(available_engines),
                "total_engines": len(engines),
                "details": {
                    "available_engines": [
                        e.get("name", "unknown") for e in available_engines
                    ],
                    "unavailable_engines": [
                        e.get("name", "unknown")
                        for e in engines
                        if not e.get("available", False)
                    ],
                },
                "timestamp": __import__("time").time(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": __import__("time").time(),
            }

    @app.get("/info")
    async def get_system_info():
        """Retrieves comprehensive system information and API capabilities.

        Provides details about available engines, voices, supported formats,
        languages, and service limits for API consumers.

        Returns:
            Dictionary with service info, capabilities, and limits

        Raises:
            HTTPException: If system information retrieval fails
        """
        try:
            engines = get_engines()
            voices = list_voices()

            return {
                "service": "TTSKit Simple API",
                "version": "0.1.0",
                "capabilities": {
                    "engines": {
                        "total": len(engines),
                        "available": len(
                            [e for e in engines if e.get("available", False)]
                        ),
                        "list": [e.get("name", "unknown") for e in engines],
                    },
                    "voices": {
                        "total": len(voices),
                        "sample": voices[:10] if len(voices) > 10 else voices,
                    },
                    "supported_formats": ["ogg", "mp3", "wav"],
                    "supported_languages": list(
                        set([e.get("lang", "en") for e in engines if e.get("lang")])
                    ),
                },
                "limits": {
                    "max_text_length": settings.max_text_length,
                    "max_batch_size": 100,
                    "rate_limits": {
                        "requests_per_minute": settings.rate_limit_rpm,
                        "concurrent_requests": 10,
                    },
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get system info: {str(e)}"
            ) from e

    return app


def create_batch_api() -> FastAPI:
    """Creates a FastAPI application for batch text-to-speech processing.

    Sets up endpoints for processing multiple synthesis requests in a single
    operation. Returns configured FastAPI instance for batch operations.
    """
    app = FastAPI(
        title="TTSKit Batch API",
        description="Batch text-to-speech processing API",
        version="1.0.0",
    )

    tts = TTS()

    @app.post("/batch", response_model=BatchSynthesisResponse)
    async def batch_synthesize(request: BatchSynthesisRequest):
        """Processes multiple synthesis requests in a single operation.

        Args:
            request: Batch request containing list of individual synthesis requests

        Returns:
            BatchSynthesisResponse with results for each request and summary statistics
        """
        results: List[SynthesisResponse] = []

        for synth_request in request.requests:
            try:
                config = SynthConfig(
                    text=synth_request.text,
                    lang=synth_request.lang,
                    voice=synth_request.voice,
                    engine=synth_request.engine,
                    rate=synth_request.rate,
                    pitch=synth_request.pitch,
                    output_format=synth_request.output_format,
                    cache=True,
                )

                audio_out = await tts.synth_async(config)

                results.append(
                    SynthesisResponse(
                        success=True,
                        duration=audio_out.duration,
                        size=audio_out.size,
                        format=audio_out.format,
                        engine_used=synth_request.engine or "auto",
                    )
                )

            except TextValidationError as e:
                results.append(
                    SynthesisResponse(
                        success=False, error=f"Text validation failed: {str(e)}"
                    )
                )
            except EngineNotFoundError as e:
                results.append(
                    SynthesisResponse(
                        success=False, error=f"Engine not found: {str(e)}"
                    )
                )
            except AudioConversionError as e:
                results.append(
                    SynthesisResponse(
                        success=False, error=f"Audio conversion failed: {str(e)}"
                    )
                )
            except AllEnginesFailedError as e:
                results.append(
                    SynthesisResponse(
                        success=False, error=f"All engines failed: {str(e)}"
                    )
                )
            except TTSError as e:
                results.append(
                    SynthesisResponse(success=False, error=f"TTS error: {str(e)}")
                )
            except Exception as e:
                results.append(
                    SynthesisResponse(
                        success=False, error=f"Unexpected error: {str(e)}"
                    )
                )

        successful_count = len([r for r in results if r.success])
        failed_count = len(results) - successful_count

        return BatchSynthesisResponse(
            results=results,
            total=len(request.requests),
            successful=successful_count,
            failed=failed_count,
        )

    return app


def test_api():
    """Demonstrates how to test the TTSKit API endpoints.

    Shows example requests and provides curl commands for testing synthesis,
    batch processing, and accessing interactive documentation.
    """
    print("🧪 Testing TTSKit API")
    print("=" * 50)

    test_requests = [
        SynthesisRequest(text="Hello, world!", lang="en", engine="gtts"),
        SynthesisRequest(
            text="سلام دنیا!",
            lang="fa",
            engine="edge",
            voice="fa-IR-DilaraNeural",
        ),
        SynthesisRequest(
            text="مرحبا بالعالم!",
            lang="ar",
            engine="edge",
            voice="ar-SA-HamedNeural",
        ),
    ]

    print("Test requests:")
    for i, req in enumerate(test_requests):
        print(f"  {i + 1}. {req.text} ({req.lang})")

    print("\nTo test the API:")
    print("1. Start the server: python examples/02_fastapi.py")
    print("2. Test with curl (JSON format):")
    print("   curl -X POST 'http://localhost:8000/synthesize' \\")
    print("        -H 'Content-Type: application/json' \\")
    print(
        '        -d \'{"text": "Hello world", "lang": "en", "output_format": "ogg"}\' \\'
    )
    print("        --output hello.ogg")
    print("\n3. Test batch processing:")
    print("   curl -X POST 'http://localhost:8000/batch' \\")
    print("        -H 'Content-Type: application/json' \\")
    print(
        '        -d \'{"requests": [{"text": "Hello", "lang": "en"}, {"text": "سلام", "lang": "fa"}]}\''
    )
    print("\n4. Or visit http://localhost:8000/docs for interactive API documentation")


def main():
    """Runs the FastAPI example server with TTSKit integration.

    Creates and starts a simple API server, displays available endpoints,
    shows testing instructions, and handles graceful shutdown.
    """
    print("🚀 TTSKit FastAPI Examples")
    print("=" * 50)

    simple_app = create_simple_api()

    print("Available APIs:")
    print("1. Simple API - Basic synthesis endpoints")
    print("2. Batch API - Batch processing endpoints")
    print("3. Full API - Complete TTSKit API (from ttskit.api.app)")

    print("\nStarting Simple API server...")
    print("Visit http://localhost:8000/docs for API documentation")
    print("Press Ctrl+C to stop")

    test_api()

    try:
        uvicorn.run(
            simple_app,
            host=getattr(settings, "api_host", "127.0.0.1"),
            port=getattr(settings, "api_port", 8000),
            log_level="info",
            access_log=True,
        )
    except KeyboardInterrupt:
        print("\n✅ Server stopped gracefully")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        raise


if __name__ == "__main__":
    main()
