#!/usr/bin/env python3
"""TTSKit Benchmark Script - See how fast your TTS engines really are."""

import asyncio
import time
from pathlib import Path

from ttskit import TTS
from ttskit.engines import EdgeEngine, GTTSEngine
from ttskit.utils.audio import get_audio_info, to_opus_ogg


async def benchmark_engine(engine, text: str, lang: str, iterations: int = 3) -> dict:
    """Tests how fast a TTS engine is by running it several times.
    
    Args:
        engine: TTS engine to test
        text: Text to synthesize for the test
        lang: Language code to use
        iterations: How many times to run the test
        
    Returns:
        Dictionary with timing stats, file sizes, and other useful metrics
    """
    print(f"🔧 Benchmarking {engine.__class__.__name__} for '{text[:30]}...'")

    times = []
    file_sizes = []

    for i in range(iterations):
        start_time = time.time()

        mp3_path = engine.synth_to_mp3(text, lang)

        ogg_path = f"benchmark_{i}.ogg"
        to_opus_ogg(mp3_path, ogg_path)

        end_time = time.time()
        duration = end_time - start_time
        times.append(duration)

        if Path(ogg_path).exists():
            info = get_audio_info(ogg_path)
            file_sizes.append(Path(ogg_path).stat().st_size)
            print(
                f"  Iteration {i + 1}: {duration:.2f}s, {info['duration']:.1f}s audio, {file_sizes[-1]} bytes"
            )

        Path(mp3_path).unlink(missing_ok=True)
        Path(ogg_path).unlink(missing_ok=True)

    return {
        "engine": engine.__class__.__name__,
        "text_length": len(text),
        "language": lang,
        "iterations": iterations,
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "avg_file_size": sum(file_sizes) / len(file_sizes) if file_sizes else 0,
    }


async def run_benchmarks():
    """Runs speed tests on different TTS engines with various text types.
    
    Tests short text, long text, and different languages to see how each
    engine performs. Great for figuring out which engine works best for
    your specific use case.
    """
    print("🚀 TTSKit Performance Benchmarks")
    print("=" * 50)

    test_cases = [
        ("سلام دنیا! این یک تست فارسی است.", "fa"),
        ("Hello world! This is an English test.", "en"),
        ("مرحبا! هذا اختبار باللغة العربية.", "ar"),
        ("A" * 200, "en"),
        ("سلام " * 50, "fa"),
    ]

    engines = [
        GTTSEngine(default_lang="en"),
        EdgeEngine(default_lang="en"),
    ]

    results = []

    for text, lang in test_cases:
        print(f"\n📝 Testing: '{text[:50]}{'...' if len(text) > 50 else ''}' ({lang})")
        print("-" * 40)

        for engine in engines:
            try:
                result = await benchmark_engine(engine, text, lang)
                results.append(result)
            except Exception as e:
                print(f"  ❌ Error with {engine.__class__.__name__}: {e}")

    print("\n📊 Benchmark Summary")
    print("=" * 50)

    for result in results:
        print(f"Engine: {result['engine']}")
        print(f"  Language: {result['language']}")
        print(f"  Text Length: {result['text_length']} chars")
        print(f"  Avg Time: {result['avg_time']:.2f}s")
        print(f"  Time Range: {result['min_time']:.2f}s - {result['max_time']:.2f}s")
        print(f"  Avg File Size: {result['avg_file_size']:.0f} bytes")
        print()


async def test_router_performance():
    """Tests how fast the engine router picks the right engine for each language.
    
    Measures how long it takes to choose an engine for different languages.
    Should be pretty fast since it's just looking up which engine to use.
    """
    print("\n🔀 Router Performance Test")
    print("-" * 30)

    tts = TTS(default_lang="en")

    languages = ["fa", "en", "ar", "es", "fr", "de"]

    for lang in languages:
        start_time = time.time()
        engine = tts.router.select_engine(lang)
        end_time = time.time()

        print(f"{lang}: {engine} - {end_time - start_time:.4f}s")


async def test_cache_performance():
    """Tests how much faster things get when using the cache.
    
    Generates audio once, then gets it from cache the second time to show
    the speed difference. Cache should be way faster than generating fresh.
    """
    print("\n💾 Cache Performance Test")
    print("-" * 30)

    from ttskit.utils.audio_manager import audio_manager

    test_text = "test text"
    test_lang = "en"
    test_engine = "gtts"

    start_time = time.time()
    audio_data = await audio_manager.get_audio(test_text, test_lang, test_engine)
    set_time = time.time() - start_time

    start_time = time.time()
    cached_audio = await audio_manager.get_audio(test_text, test_lang, test_engine)
    get_time = time.time() - start_time

    print(f"First generation: {set_time:.4f}s")
    print(f"Cached retrieval: {get_time:.4f}s")
    print(f"Speedup: {set_time / get_time:.1f}x")
    print(f"Data matches: {audio_data == cached_audio}")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
    asyncio.run(test_router_performance())
    asyncio.run(test_cache_performance())
