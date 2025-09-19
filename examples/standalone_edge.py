#!/usr/bin/env python3
"""Standalone EdgeEngine example - can be used independently."""

import os

from ttskit.engines.edge_engine import EdgeEngine


def simple_edge_example():
    """Demonstrates EdgeEngine usage as a standalone component without full TTSKit.
    
    Shows direct engine instantiation, multi-language synthesis, file creation
    verification, and cleanup operations for independent Edge TTS usage.
    """
    print("🎤 Standalone EdgeEngine Example")
    print("=" * 40)

    try:
        edge = EdgeEngine(default_lang="en")

        test_cases = [
            ("Hello world!", "en"),
            ("سلام دنیا!", "fa"),
            ("مرحبا بالعالم!", "ar"),
            ("Hola mundo!", "es"),
        ]

        for text, lang in test_cases:
            print(f"\n📝 Synthesizing: '{text}' in {lang}")

            try:
                mp3_path = edge.synth_to_mp3(text, lang)

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

    except ImportError as e:
        print(f"❌ Edge TTS not available: {e}")
        print("Install with: pip install edge-tts")


def voice_mapping_example():
    """Displays the language-to-voice mapping used by EdgeEngine.
    
    Shows how different language codes are mapped to specific Edge TTS voices
    for consistent voice selection across different languages.
    """
    print("\n🎵 Voice Mapping Example")
    print("-" * 30)

    try:
        from ttskit.engines.edge_engine import VOICE_BY_LANG

        for lang, voice in VOICE_BY_LANG.items():
            print(f"{lang} → {voice}")

    except ImportError:
        print("Edge TTS not available")


if __name__ == "__main__":
    simple_edge_example()
    voice_mapping_example()
