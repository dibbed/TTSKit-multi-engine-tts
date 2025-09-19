#!/usr/bin/env python3
"""AudioManager Example - Managing your TTS audio files made easy.

Shows how to use AudioManager for handling audio files, caching,
format conversion, and cleanup without the hassle.
"""

import asyncio
from pathlib import Path

from ttskit.utils.audio_manager import AudioManager, audio_manager
from ttskit.utils.logging_config import get_logger

logger = get_logger(__name__)


async def basic_usage_example():
    """Shows the basics of using AudioManager for everyday TTS tasks.
    
    Simple audio generation and file saving - the stuff you'll probably
    use most often when working with text-to-speech.
    """
    print("=== Basic AudioManager Usage ===")

    audio_data = await audio_manager.get_audio(
        text="سلام دنیا! این یک تست است.", lang="fa", engine="gtts", format="mp3"
    )

    print(f"Generated audio size: {len(audio_data)} bytes")

    output_path = Path("output_basic.mp3")
    output_path.write_bytes(audio_data)
    print(f"Audio saved to: {output_path}")


async def custom_manager_example():
    """Shows how to set up AudioManager with your own cache settings.
    
    Creates a custom manager with specific cache limits and generates audio
    in multiple languages. Useful when you want more control over how
    caching works.
    """
    print("\n=== Custom AudioManager Configuration ===")

    custom_manager = AudioManager(
        cache_dir="./custom_cache",
        max_cache_size=500,
        max_file_age=1800,
    )

    texts = ["Hello world!", "مرحبا بالعالم!", "Hola mundo!", "Bonjour le monde!"]

    languages = ["en", "ar", "es", "fr"]

    for text, lang in zip(texts, languages, strict=True):
        audio_data = await custom_manager.get_audio(
            text=text, lang=lang, engine="auto", format="ogg"
        )

        output_path = Path(f"output_{lang}.ogg")
        output_path.write_bytes(audio_data)
        print(f"Generated {lang}: {len(audio_data)} bytes")

    stats = custom_manager.get_cache_stats()
    print("\nCache Statistics:")
    print(f"Total files: {stats['total_files']}")
    print(f"Total size: {stats['total_size_mb']:.2f} MB")
    print(f"Cache directory: {stats['cache_dir']}")


async def cache_management_example():
    """Shows all the cache management tools you get with AudioManager.
    
    Generates some test files, shows cache stats, lists what's cached,
    and demonstrates export and cleanup features. Pretty handy for
    keeping your cache organized.
    """
    print("\n=== Cache Management Features ===")

    for i in range(5):
        audio_data = await audio_manager.get_audio(
            text=f"Test message number {i}", lang="en", engine="gtts", format="mp3"
        )
        print(f"Generated test {i}: {len(audio_data)} bytes")

    stats = audio_manager.get_cache_stats()
    print("\nCache Statistics:")
    print(f"Total files: {stats['total_files']}")
    print(f"Total size: {stats['total_size_mb']:.2f} MB")

    cached_files = audio_manager.list_cached_files()
    print(f"\nCached Files ({len(cached_files)}):")
    for file_info in cached_files[:3]:
        if file_info:
            print(f"  - {file_info['file_path']}")
            print(f"    Size: {file_info.get('file_size', 0)} bytes")
            print(f"    Age: {file_info.get('file_age', 0):.1f} seconds")

    export_dir = "./cache_export"
    audio_manager.export_cache(export_dir)
    print(f"\nCache exported to: {export_dir}")

    audio_manager.cleanup_old_files()
    print("Old files cleaned up")


async def error_handling_example():
    """Shows how AudioManager handles things when stuff goes wrong.
    
    Tests what happens with invalid engines, super long text, and other
    edge cases. Good to know how it fails so you can handle errors gracefully.
    """
    print("\n=== Error Handling ===")

    try:
        audio_data = await audio_manager.get_audio(
            text="Test", lang="en", engine="invalid_engine", format="mp3"
        )
        print(f"Generated with invalid engine: {len(audio_data)} bytes")
    except Exception as e:
        print(f"Expected error with invalid engine: {e}")

    try:
        long_text = "This is a very long text. " * 1000
        audio_data = await audio_manager.get_audio(
            text=long_text, lang="en", engine="gtts", format="mp3"
        )
        print(f"Generated long text: {len(audio_data)} bytes")
    except Exception as e:
        print(f"Error with long text: {e}")


async def performance_example():
    """Shows how much faster caching makes things.
    
    Generates the same audio twice - once fresh, once from cache - to
    demonstrate the speed boost you get from caching. Should be pretty
    dramatic!
    """
    print("\n=== Performance with Caching ===")

    import time

    text = "Performance test message for caching demonstration."

    start_time = time.time()
    audio_data1 = await audio_manager.get_audio(
        text=text, lang="en", engine="gtts", format="mp3"
    )
    first_time = time.time() - start_time
    print(f"First generation (cache miss): {first_time:.3f} seconds")

    start_time = time.time()
    audio_data2 = await audio_manager.get_audio(
        text=text, lang="en", engine="gtts", format="mp3"
    )
    second_time = time.time() - start_time
    print(f"Second generation (cache hit): {second_time:.3f} seconds")

    if audio_data1 == audio_data2:
        print("✅ Cached data matches original")
    else:
        print("❌ Cached data differs from original")

    speedup = first_time / second_time if second_time > 0 else float("inf")
    print(f"Speedup from caching: {speedup:.1f}x")


async def main():
    """Runs all the AudioManager examples to show what it can do.
    
    Goes through basic usage, custom setup, cache management, error handling,
    and performance testing. Should give you a good feel for how AudioManager
    works.
    """
    print("TTSKit AudioManager Examples")
    print("=" * 50)

    try:
        await basic_usage_example()
        await custom_manager_example()
        await cache_management_example()
        await error_handling_example()
        await performance_example()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
