#!/usr/bin/env python3
"""Basic TTSKit usage example.

This module showcases straightforward ways to use TTSKit for text-to-speech, covering sync/async synthesis, custom setups, voice discovery, and multi-language support.

Notes:
- Examples generate and save audio files in the 'examples' directory.
- Assumes TTSKit is installed with engines like 'edge' available.
"""

import asyncio
from pathlib import Path

from ttskit import TTS, SynthConfig, synth, synth_async


def basic_synthesis():
    """Demonstrates basic synchronous text-to-speech synthesis using the convenience function.

    This performs a quick TTS conversion of sample English text to audio and saves it.

    Notes:
    - Relies on the 'synth' convenience function with default settings for English.
    - Output saved as 'examples/basic_output.ogg' in OGG format.
    - Prints progress and handles any synthesis errors gracefully.
    """
    print("🎤 Basic TTSKit Synthesis Example")
    print("=" * 50)

    print("\n1. Using convenience function:")
    try:
        audio_out = synth(
            text="Hello, world! This is a test of TTSKit.",
            lang="en",
            output_format="ogg",
        )

        output_file = Path("examples/basic_output.ogg")
        audio_out.save(output_file)

        print(f"✅ Synthesized and saved to {output_file}")
        print(f"   Duration: {audio_out.duration:.1f}s")
        print(f"   Size: {audio_out.size} bytes")

    except Exception as e:
        print(f"❌ Error: {e}")


def advanced_synthesis():
    """Shows advanced synthesis using TTS class with custom configuration.

    This creates a TTS instance and applies detailed settings to synthesize Persian text.

    Notes:
    - Uses 'edge' engine with specific voice, adjusted rate (1.1x), and pitch (0.5).
    - Caches the result for efficiency.
    - Saves output to 'examples/advanced_output.ogg' and reports duration/size/format.
    - Catches and prints exceptions if synthesis fails.
    """
    print("\n2. Using TTS class with custom config:")

    try:
        tts = TTS(default_lang="en")

        config = SynthConfig(
            text="سلام! این یک تست از TTSKit است.",
            lang="fa",
            engine="edge",
            voice="fa-IR-DilaraNeural",
            rate=1.1,
            pitch=0.5,
            output_format="ogg",
            cache=True,
        )

        audio_out = tts.synth(config)

        output_file = Path("examples/advanced_output.ogg")
        audio_out.save(output_file)

        print(f"✅ Synthesized Persian text and saved to {output_file}")
        print(f"   Duration: {audio_out.duration:.1f}s")
        print(f"   Size: {audio_out.size} bytes")
        print(f"   Format: {audio_out.format}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def async_synthesis():
    """Demonstrates asynchronous text-to-speech synthesis.

    This runs non-blocking TTS for Arabic text using the async convenience function.

    Notes:
    - Specifies 'edge' engine and 'ar-SA-HamedNeural' voice.
    - Outputs to MP3 format, saved as 'examples/async_output.mp3'.
    - Awaits completion and prints details like duration and size.
    - Includes error handling for async operations.
    """
    print("\n3. Asynchronous synthesis:")

    try:
        audio_out = await synth_async(
            text="مرحبا بالعالم! هذا اختبار من TTSKit.",
            lang="ar",
            engine="edge",
            voice="ar-SA-HamedNeural",
            output_format="mp3",
        )

        output_file = Path("examples/async_output.mp3")
        audio_out.save(output_file)

        print(f"✅ Synthesized Arabic text and saved to {output_file}")
        print(f"   Duration: {audio_out.duration:.1f}s")
        print(f"   Size: {audio_out.size} bytes")

    except Exception as e:
        print(f"❌ Error: {e}")


def list_available_voices():
    """Lists all available TTS engines and their voices.

    This retrieves and prints details on engines, their status, languages, and sample voices.

    Notes:
    - Fetches engines via 'get_engines' and voices per engine with 'list_voices'.
    - Limits voice display to first 5 per engine for brevity.
    - Indicates availability with checkmarks; handles import/listing errors.
    """
    print("\n4. Available voices:")

    try:
        from ttskit import get_engines, list_voices

        engines = get_engines()
        print(f"Available engines: {len(engines)}")

        for engine in engines:
            print(f"\n🔧 {engine['name'].upper()}")
            print(f"   Available: {'✅' if engine['available'] else '❌'}")
            print(f"   Languages: {', '.join(engine.get('languages', []))}")

            voices = list_voices(engine=engine["name"])
            print(f"   Voices: {len(voices)}")
            if voices:
                for voice in voices[:5]:
                    print(f"     • {voice}")
                if len(voices) > 5:
                    print(f"     ... and {len(voices) - 5} more")

    except Exception as e:
        print(f"❌ Error: {e}")


def multiple_languages():
    """Demonstrates synthesis across multiple languages.

    This synthesizes a greeting in English, Persian, Arabic, Spanish, and French, saving each separately.

    Notes:
    - Uses TTS instance with SynthConfig for each language's text and code.
    - Outputs OGG files named 'examples/multilang_{lang}.ogg'.
    - Prints per-language status and duration; catches individual errors.
    """
    print("\n5. Multiple languages synthesis:")

    languages = [
        ("Hello, world!", "en", "English"),
        ("سلام دنیا!", "fa", "Persian"),
        ("مرحبا بالعالم!", "ar", "Arabic"),
        ("Hola mundo!", "es", "Spanish"),
        ("Bonjour le monde!", "fr", "French"),
    ]

    tts = TTS()

    for text, lang, name in languages:
        try:
            print(f"\n   {name} ({lang}): {text}")

            config = SynthConfig(text=text, lang=lang, output_format="ogg")

            audio_out = tts.synth(config)

            output_file = Path(f"examples/multilang_{lang}.ogg")
            audio_out.save(output_file)

            print(f"   ✅ Saved to {output_file} ({audio_out.duration:.1f}s)")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def main():
    """Runs all basic TTSKit usage examples.

    This orchestrates the full demo: sets up directory, runs synthesis functions, lists voices, and summarizes outputs.

    Notes:
    - Ensures 'examples' directory exists before running.
    - Executes sync functions directly, async via asyncio.run.
    - Lists generated OGG/MP3 files at the end.
    - All operations print status for user feedback.
    """
    print("🚀 TTSKit Basic Usage Examples")
    print("=" * 50)

    Path("examples").mkdir(exist_ok=True)

    basic_synthesis()
    advanced_synthesis()

    asyncio.run(async_synthesis())

    list_available_voices()
    multiple_languages()

    print("\n🎉 All examples completed!")
    print("\nGenerated files:")
    for file in Path("examples").glob("*.ogg"):
        print(f"  • {file}")
    for file in Path("examples").glob("*.mp3"):
        print(f"  • {file}")


if __name__ == "__main__":
    main()
