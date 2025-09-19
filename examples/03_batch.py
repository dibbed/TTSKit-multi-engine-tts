#!/usr/bin/env python3
"""Batch processing example for TTSKit.

This example demonstrates how to process multiple text-to-speech requests efficiently.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from ttskit import TTS, SynthConfig


class BatchProcessor:
    """Handles batch processing of multiple TTS synthesis requests.
    
    Manages concurrent synthesis operations with configurable limits to prevent
    resource exhaustion while maximizing throughput.
    """

    def __init__(self, max_concurrent: int = 5):
        """Initializes batch processor with concurrency control.

        Args:
            max_concurrent: Maximum number of concurrent synthesis tasks
        """
        self.max_concurrent = max_concurrent
        self.tts = TTS()
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_single(self, request: dict[str, Any]) -> dict[str, Any]:
        """Processes a single synthesis request with timing and error handling.

        Args:
            request: Dictionary containing synthesis parameters (text, lang, voice, etc.)

        Returns:
            Dictionary with synthesis results including success status, audio metadata,
            processing time, and error information if applicable
        """
        async with self.semaphore:
            try:
                config = SynthConfig(
                    text=request.get("text", ""),
                    lang=request.get("lang", "en"),
                    voice=request.get("voice"),
                    engine=request.get("engine"),
                    rate=request.get("rate", 1.0),
                    pitch=request.get("pitch", 0.0),
                    output_format=request.get("format", "ogg"),
                    cache=True,
                )

                start_time = time.time()
                audio_out = await self.tts.synth_async(config)
                duration = time.time() - start_time

                return {
                    "success": True,
                    "text": request.get("text", ""),
                    "lang": request.get("lang", "en"),
                    "engine": request.get("engine", "auto"),
                    "duration": audio_out.duration,
                    "size": audio_out.size,
                    "format": audio_out.format,
                    "processing_time": duration,
                    "error": None,
                }

            except Exception as e:
                return {
                    "success": False,
                    "text": request.get("text", ""),
                    "lang": request.get("lang", "en"),
                    "engine": request.get("engine", "auto"),
                    "duration": 0,
                    "size": 0,
                    "format": request.get("format", "ogg"),
                    "processing_time": 0,
                    "error": str(e),
                }

    async def process_batch(self, requests: list[dict[str, Any]]) -> dict[str, Any]:
        """Processes multiple synthesis requests concurrently with comprehensive statistics.

        Args:
            requests: List of synthesis request dictionaries

        Returns:
            Dictionary containing batch results, success/failure counts, timing statistics,
            audio metadata totals, throughput metrics, and individual request results
        """
        start_time = time.time()

        tasks = [self.process_single(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "success": False,
                        "text": requests[i].get("text", ""),
                        "lang": requests[i].get("lang", "en"),
                        "engine": requests[i].get("engine", "auto"),
                        "duration": 0,
                        "size": 0,
                        "format": requests[i].get("format", "ogg"),
                        "processing_time": 0,
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        total_time = time.time() - start_time

        successful = [r for r in processed_results if r["success"]]
        failed = [r for r in processed_results if not r["success"]]

        total_audio_duration = sum(r["duration"] for r in successful)
        total_audio_size = sum(r["size"] for r in successful)
        avg_processing_time = sum(
            r["processing_time"] for r in processed_results
        ) / len(processed_results)

        return {
            "total_requests": len(requests),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(requests) * 100,
            "total_processing_time": total_time,
            "total_audio_duration": total_audio_duration,
            "total_audio_size": total_audio_size,
            "average_processing_time": avg_processing_time,
            "throughput": len(requests) / total_time,
            "results": processed_results,
        }


def create_test_requests() -> list[dict[str, Any]]:
    """Creates a diverse set of test synthesis requests for demonstration.

    Returns:
        List of request dictionaries with various languages, engines, and formats
    """
    return [
        {"text": "Hello, world!", "lang": "en", "engine": "gtts", "format": "ogg"},
        {
            "text": "سلام دنیا!",
            "lang": "fa",
            "engine": "edge",
            "voice": "fa-IR-DilaraNeural",
            "format": "ogg",
        },
        {
            "text": "مرحبا بالعالم!",
            "lang": "ar",
            "engine": "edge",
            "voice": "ar-SA-HamedNeural",
            "format": "ogg",
        },
        {
            "text": "Hola mundo!",
            "lang": "es",
            "engine": "edge",
            "voice": "es-ES-ElviraNeural",
            "format": "mp3",
        },
        {
            "text": "Bonjour le monde!",
            "lang": "fr",
            "engine": "edge",
            "voice": "fr-FR-DeniseNeural",
            "format": "wav",
        },
        {
            "text": "Hallo Welt!",
            "lang": "de",
            "engine": "edge",
            "voice": "de-DE-KatjaNeural",
            "format": "ogg",
        },
        {
            "text": "Ciao mondo!",
            "lang": "it",
            "engine": "edge",
            "voice": "it-IT-ElsaNeural",
            "format": "ogg",
        },
        {
            "text": "Olá mundo!",
            "lang": "pt",
            "engine": "edge",
            "voice": "pt-BR-FranciscaNeural",
            "format": "mp3",
        },
        {
            "text": "Привет мир!",
            "lang": "ru",
            "engine": "edge",
            "voice": "ru-RU-SvetlanaNeural",
            "format": "ogg",
        },
        {
            "text": "こんにちは世界！",
            "lang": "ja",
            "engine": "edge",
            "voice": "ja-JP-NanamiNeural",
            "format": "ogg",
        },
    ]


def create_large_batch_requests(count: int = 100) -> list[dict[str, Any]]:
    """Creates a large batch of test requests by cycling through base templates.

    Args:
        count: Number of requests to generate

    Returns:
        List of request dictionaries with numbered variations of base texts
    """
    base_requests = [
        {"text": "Hello, world!", "lang": "en", "engine": "gtts"},
        {
            "text": "سلام دنیا!",
            "lang": "fa",
            "engine": "edge",
            "voice": "fa-IR-DilaraNeural",
        },
        {
            "text": "مرحبا بالعالم!",
            "lang": "ar",
            "engine": "edge",
            "voice": "ar-SA-HamedNeural",
        },
        {
            "text": "Hola mundo!",
            "lang": "es",
            "engine": "edge",
            "voice": "es-ES-ElviraNeural",
        },
        {
            "text": "Bonjour le monde!",
            "lang": "fr",
            "engine": "edge",
            "voice": "fr-FR-DeniseNeural",
        },
    ]

    requests = []
    for i in range(count):
        base_request = base_requests[i % len(base_requests)].copy()
        base_request["text"] = f"{base_request['text']} (Request {i + 1})"
        base_request["format"] = "ogg"
        requests.append(base_request)

    return requests


async def test_batch_processing():
    """Demonstrates batch processing functionality with detailed performance metrics.
    
    Creates test requests, processes them concurrently, and displays comprehensive
    statistics including success rates, timing, and individual results.
    """
    print("🧪 Testing Batch Processing")
    print("=" * 50)

    test_requests = create_test_requests()

    print(f"Processing {len(test_requests)} test requests...")

    processor = BatchProcessor(max_concurrent=3)

    start_time = time.time()
    results = await processor.process_batch(test_requests)
    total_time = time.time() - start_time

    print("\n📊 Batch Processing Results:")
    print(f"Total requests: {results['total_requests']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Success rate: {results['success_rate']:.1f}%")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Total audio duration: {results['total_audio_duration']:.1f}s")
    print(f"Total audio size: {results['total_audio_size']:,} bytes")
    print(f"Average processing time: {results['average_processing_time']:.2f}s")
    print(f"Throughput: {results['throughput']:.1f} requests/second")

    print("\n📝 Individual Results:")
    for i, result in enumerate(results["results"]):
        status = "✅" if result["success"] else "❌"
        print(
            f"  {i + 1:2d}. {status} {result['text'][:30]}... ({result['lang']}) - {result['processing_time']:.2f}s"
        )
        if not result["success"]:
            print(f"      Error: {result['error']}")


async def test_large_batch():
    """Demonstrates large-scale batch processing with higher concurrency.
    
    Tests system performance with 50 requests processed with increased
    concurrency limits to show scalability characteristics.
    """
    print("\n🚀 Testing Large Batch Processing")
    print("=" * 50)

    large_requests = create_large_batch_requests(50)

    print(f"Processing {len(large_requests)} requests...")

    processor = BatchProcessor(max_concurrent=10)

    start_time = time.time()
    results = await processor.process_batch(large_requests)
    total_time = time.time() - start_time

    print("\n📊 Large Batch Results:")
    print(f"Total requests: {results['total_requests']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Success rate: {results['success_rate']:.1f}%")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Throughput: {results['throughput']:.1f} requests/second")
    print(f"Average processing time: {results['average_processing_time']:.2f}s")


def save_results_to_file(results: dict[str, Any], filename: str):
    """Saves batch processing results to a JSON file.

    Args:
        results: Dictionary containing batch processing results and statistics
        filename: Path where the JSON file should be saved
    """
    clean_results = results.copy()
    for result in clean_results.get("results", []):
        if "audio_data" in result:
            del result["audio_data"]

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {filename}")


async def main():
    """Runs comprehensive batch processing examples and demonstrations.
    
    Creates output directory, executes small and large batch tests,
    and displays completion summary.
    """
    print("🚀 TTSKit Batch Processing Examples")
    print("=" * 50)

    Path("examples").mkdir(exist_ok=True)

    await test_batch_processing()

    await test_large_batch()

    print("\n🎉 Batch processing examples completed!")
    print("\nGenerated files in examples/ directory")


if __name__ == "__main__":
    asyncio.run(main())
