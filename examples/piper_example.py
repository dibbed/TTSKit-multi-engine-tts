#!/usr/bin/env python3
"""
Simple example for using Piper TTS in TTSKit

This example shows how to use the new Piper TTS engine.
"""

import asyncio
from pathlib import Path

from ttskit import TTS, SynthConfig


async def main():
    """Demonstrates Piper TTS engine usage with model validation and synthesis.

    Checks for required voice models, creates TTS instance, lists available engines,
    performs test synthesis, and saves the resulting audio file with detailed
    audio information display.
    """

    voices_dir = Path("./models/piper")
    if not voices_dir.exists():
        print("❌ Voices directory does not exist!")
        print("Please download voice models first:")
        print(
            "python3 -m piper.download_voices fa_IR-amir-medium --data-dir ./models/piper"
        )
        return

    onnx_files = list(voices_dir.glob("*.onnx"))
    if not onnx_files:
        print("❌ No .onnx model files found in voices directory!")
        print("Please download voice models first:")
        print(
            "python3 -m piper.download_voices fa_IR-amir-medium --data-dir ./models/piper"
        )
        return

    print(f"✅ Found {len(onnx_files)} model files:")
    for file in onnx_files:
        print(f"  - {file.name}")

    try:
        print("\n🚀 Creating TTS instance...")
        tts = TTS(default_lang="fa")

        print("\n📋 Available engines:")
        engines = tts.router.registry.get_available_engines()
        for engine in engines:
            print(f"  - {engine}")

        print("\n🎵 Testing synthesis with Piper...")

        test_text = "Hello, this is a test of Piper TTS. I hope the voice is clear."

        config = SynthConfig(
            text=test_text,
            lang="fa",
            engine="piper",
            rate=1.0,
            output_format="wav",
        )

        audio_output = await tts.synth_async(config)

        print("✅ Synthesis successful!")
        print("📊 Audio information:")
        print(f"  - Format: {audio_output.format}")
        print(f"  - Duration: {audio_output.duration:.2f} seconds")
        print(f"  - Sample rate: {audio_output.sample_rate} Hz")
        print(f"  - Channels: {audio_output.channels}")
        print(f"  - File size: {audio_output.size} bytes")

        output_file = "piper_test_output.wav"
        with open(output_file, "wb") as f:
            f.write(audio_output.data)

        print(f"💾 Audio file saved: {output_file}")

    except Exception as e:
        print(f"❌ Synthesis error: {e}")
        print("\n🔧 Possible solutions:")
        print("1. Make sure piper-tts is installed: pip install piper-tts")
        print("2. Make sure voice models are downloaded")
        print("3. Check that voices path in settings is correct")


async def test_different_voices():
    """Tests multiple Piper voices with synthesis and performance measurement.

    Lists available Piper voices, tests the first three voices with sample text,
    and displays synthesis results including duration and success status.
    """

    print("\n🎭 Testing different voices...")

    try:
        tts = TTS(default_lang="fa")

        voices = tts.router.registry.get_engine("piper").list_voices()
        print(f"📋 Available voices: {voices}")

        if not voices:
            print("❌ No voices found!")
            return

        for voice in voices[:3]:
            print(f"\n🎵 Testing voice: {voice}")

            config = SynthConfig(
                text=f"This is a test of voice {voice}.",
                lang="fa",
                engine="piper",
                voice=voice,
                output_format="wav",
            )

            try:
                audio_output = await tts.synth_async(config)
                print(f"✅ Success: {audio_output.duration:.2f}s")
            except Exception as e:
                print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Error testing voices: {e}")


if __name__ == "__main__":
    print("🎤 Piper TTS Example for TTSKit")
    print("=" * 50)

    asyncio.run(main())

    asyncio.run(test_different_voices())

    print("\n✨ Example completed!")
