#!/usr/bin/env python3
"""Example usage of TTSKit API."""

import asyncio
import base64
from pathlib import Path

import httpx


class TTSKitAPIClient:
    """HTTP client for interacting with TTSKit API endpoints.
    
    Provides methods for synthesis, batch processing, voice listing, engine information,
    health checks, and cache statistics. Handles authentication and request formatting.
    """

    def __init__(
        self, base_url: str = "http://localhost:8000", api_key: str = "demo-key"
    ):
        """Initializes API client with base URL and authentication.
        
        Args:
            base_url: TTSKit API server base URL
            api_key: Authentication key for API access
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def synthesize(
        self,
        text: str,
        lang: str = "en",
        engine: str = None,
        voice: str = None,
        format: str = "ogg",
        rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """Synthesizes text to speech via API and returns audio data.
        
        Args:
            text: Text to synthesize
            lang: Language code (default: "en")
            engine: TTS engine to use (optional)
            voice: Specific voice name (optional)
            format: Audio format ("ogg", "mp3", "wav")
            rate: Speech rate multiplier
            pitch: Pitch adjustment in semitones
            
        Returns:
            Raw audio data as bytes
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/synth",
                headers=self.headers,
                json={
                    "text": text,
                    "lang": lang,
                    "engine": engine,
                    "voice": voice,
                    "format": format,
                    "rate": rate,
                    "pitch": pitch,
                },
            )
            response.raise_for_status()
            return response.content

    async def batch_synthesize(
        self,
        texts: list[str],
        lang: str = "en",
        engine: str = None,
        voice: str = None,
        format: str = "ogg",
    ) -> dict:
        """Synthesizes multiple texts in a single batch request.
        
        Args:
            texts: List of text strings to synthesize
            lang: Language code for all texts
            engine: TTS engine to use (optional)
            voice: Specific voice name (optional)
            format: Audio format for all outputs
            
        Returns:
            Dictionary with batch results including success counts and audio data
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/synth/batch",
                headers=self.headers,
                json={
                    "texts": texts,
                    "lang": lang,
                    "engine": engine,
                    "voice": voice,
                    "format": format,
                },
            )
            response.raise_for_status()
            return response.json()

    async def preview_synthesis(
        self, text: str, lang: str = "en", engine: str = None, voice: str = None
    ) -> dict:
        """Previews synthesis parameters without generating audio.
        
        Args:
            text: Text to preview
            lang: Language code
            engine: TTS engine to use (optional)
            voice: Specific voice name (optional)
            
        Returns:
            Dictionary with preview information including estimated duration and text analysis
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/synth/preview",
                headers=self.headers,
                params={
                    "text": text,
                    "lang": lang,
                    "engine": engine,
                    "voice": voice,
                },
            )
            response.raise_for_status()
            return response.json()

    async def list_engines(self) -> list[dict]:
        """Retrieves list of available TTS engines with their capabilities.
        
        Returns:
            List of dictionaries containing engine information including names,
            availability status, and supported languages
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/engines",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_voices(self, engine: str = None, language: str = None) -> list[dict]:
        """Retrieves available voices with optional filtering.
        
        Args:
            engine: Filter by specific engine name (optional)
            language: Filter by language code (optional)
            
        Returns:
            List of dictionaries containing voice information including names,
            languages, and associated engines
        """
        async with httpx.AsyncClient() as client:
            params = {}
            if engine:
                params["engine"] = engine
            if language:
                params["language"] = language

            response = await client.get(
                f"{self.base_url}/api/v1/voices",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_health(self) -> dict:
        """Retrieves API service health status and engine availability.
        
        Returns:
            Dictionary with health status, uptime, and engine availability information
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def get_cache_stats(self) -> dict:
        """Retrieves cache performance statistics and metrics.
        
        Returns:
            Dictionary with cache hit rates, entry counts, and performance metrics
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/cache/stats",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()


async def main():
    """Demonstrates comprehensive TTSKit API usage with various endpoints.
    
    Shows health checking, engine and voice listing, synthesis preview,
    single and batch synthesis, file saving, and cache statistics retrieval.
    """
    client = TTSKitAPIClient()

    print("🚀 TTSKit API Example")
    print("=" * 50)

    try:
        health = await client.get_health()
        print(f"✅ Service Status: {health['status']}")
        print(f"📊 Available Engines: {health['engines']}")
        print(f"⏱️  Uptime: {health['uptime']:.1f}s")
        print()
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    try:
        engines = await client.list_engines()
        print("🔧 Available Engines:")
        for engine in engines:
            status = "✅" if engine["available"] else "❌"
            print(f"  {status} {engine['name']} - {len(engine['languages'])} languages")
        print()
    except Exception as e:
        print(f"❌ Failed to list engines: {e}")

    try:
        voices = await client.list_voices()
        print("🎤 Available Voices:")
        for voice in voices[:5]:
            print(f"  • {voice['name']} ({voice['language']}) - {voice['engine']}")
        if len(voices) > 5:
            print(f"  ... and {len(voices) - 5} more voices")
        print()
    except Exception as e:
        print(f"❌ Failed to list voices: {e}")

    try:
        preview = await client.preview_synthesis(
            text="سلام دنیا", lang="fa", engine="piper"
        )
        print("🔍 Synthesis Preview:")
        print(f"  Text: {preview['text_preview']}")
        print(f"  Length: {preview['text_length']} characters")
        print(f"  Estimated Duration: {preview['estimated_duration']:.2f}s")
        print()
    except Exception as e:
        print(f"❌ Preview failed: {e}")

    try:
        print("🎵 Synthesizing single text...")
        audio_data = await client.synthesize(
            text="Hello, world!", lang="en", engine="piper", format="wav"
        )

        output_file = "api_example_output.wav"
        Path(output_file).write_bytes(audio_data)
        print(f"✅ Audio saved to: {output_file}")
        print(f"📊 File size: {len(audio_data)} bytes")
        print()
    except Exception as e:
        print(f"❌ Single synthesis failed: {e}")

    try:
        print("🎵 Synthesizing multiple texts...")
        texts = ["Hello", "World", "TTSKit"]

        batch_result = await client.batch_synthesize(
            texts=texts, lang="en", engine="piper", format="wav"
        )

        print("✅ Batch synthesis completed:")
        print(f"  Total: {batch_result['total']}")
        print(f"  Successful: {batch_result['successful']}")
        print(f"  Failed: {batch_result['failed']}")

        for i, result in enumerate(batch_result["results"]):
            if result["success"]:
                audio_data = base64.b64decode(result["audio_base64"])
                output_file = f"api_batch_{i}.wav"
                Path(output_file).write_bytes(audio_data)
                print(f"  📁 Saved: {output_file}")
        print()
    except Exception as e:
        print(f"❌ Batch synthesis failed: {e}")

    try:
        cache_stats = await client.get_cache_stats()
        print("📊 Cache Statistics:")
        print(f"  Enabled: {cache_stats['enabled']}")
        print(f"  Hits: {cache_stats['hits']}")
        print(f"  Misses: {cache_stats['misses']}")
        print(f"  Hit Rate: {cache_stats['hit_rate']:.1%}")
        print(f"  Entries: {cache_stats['entries']}")
        print()
    except Exception as e:
        print(f"❌ Failed to get cache stats: {e}")

    print("🎉 API Example completed!")


if __name__ == "__main__":
    asyncio.run(main())
