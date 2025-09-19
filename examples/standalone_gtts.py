#!/usr/bin/env python3
"""Standalone GTTSEngine example - can be used independently."""

import os

from ttskit.engines.gtts_engine import GTTSEngine


def simple_tts_example():
    """Demonstrates GTTSEngine usage as a standalone component without full TTSKit.
    
    Shows direct engine instantiation, multi-language synthesis using Google TTS,
    file creation verification, and cleanup operations for independent usage.
    """
    print("🎤 Standalone GTTSEngine Example")
    print("=" * 40)

    gtts = GTTSEngine(default_lang="en")

    test_cases = [
        ("Hello world!", "en"),
        ("مرحبا بالعالم!", "ar"),
        ("Hola mundo!", "es"),
        ("Bonjour le monde!", "fr"),
    ]

    for text, lang in test_cases:
        print(f"\n📝 Synthesizing: '{text}' in {lang}")

        try:
            mp3_path = gtts.synth_to_mp3(text, lang)

            if os.path.exists(mp3_path):
                file_size = os.path.getsize(mp3_path)
                print(f"✅ Success! File: {mp3_path}")
                print(f"   Size: {file_size} bytes")

                os.unlink(mp3_path)
                os.rmdir(os.path.dirname(mp3_path))
            else:
                print("❌ File not created")

        except Exception as e:
            print(f"❌ Error: {e}")


def language_mapping_example():
    """Displays the language mapping used by GTTSEngine for Google TTS compatibility.
    
    Shows how different language codes are mapped to Google TTS-compatible
    language identifiers for proper synthesis across various languages.
    """
    print("\n🌍 Language Mapping Example")
    print("-" * 30)

    gtts = GTTSEngine()

    for lang, mapped_lang in gtts.LANGUAGE_MAP.items():
        print(f"{lang} → {mapped_lang}")


if __name__ == "__main__":
    simple_tts_example()
    language_mapping_example()
