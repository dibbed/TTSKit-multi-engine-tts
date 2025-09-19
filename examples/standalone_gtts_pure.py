#!/usr/bin/env python3
"""Pure standalone GTTSEngine example - no package dependencies."""

import os
import tempfile

from gtts import gTTS


class StandaloneGTTSEngine:
    """Minimal standalone Google TTS engine with no external package dependencies.
    
    Provides basic text-to-speech synthesis using Google TTS with language mapping
    and temporary file management for independent usage scenarios.
    """

    LANGUAGE_MAP = {
        "fa": "en",
        "ar": "ar",
        "en": "en",
        "es": "es",
        "fr": "fr",
        "de": "de",
    }

    def __init__(self, default_lang: str | None = None) -> None:
        """Initializes the standalone engine with default language setting.
        
        Args:
            default_lang: Default language code for synthesis (defaults to "en")
        """
        self.default_lang = default_lang or "en"

    def synth_to_mp3(self, text: str, lang: str | None = None) -> str:
        """Synthesizes text to MP3 file using Google TTS with language mapping.
        
        Args:
            text: Text to synthesize
            lang: Language code (uses default if not specified)
            
        Returns:
            Path to generated MP3 file in temporary directory
        """
        lang = lang or self.default_lang
        gtts_lang = self.LANGUAGE_MAP.get(lang, "en")
        td = tempfile.mkdtemp(prefix="tts_")
        mp3_path = os.path.join(td, "synth.mp3")
        tts = gTTS(text=text, lang=gtts_lang)
        tts.save(mp3_path)
        return mp3_path


def main():
    """Demonstrates pure standalone Google TTS usage without TTSKit dependencies.
    
    Shows engine instantiation, multi-language synthesis, file verification,
    cleanup operations, and language mapping display for minimal TTS integration.
    """
    print("🎤 Pure Standalone GTTSEngine Example")
    print("=" * 50)

    gtts = StandaloneGTTSEngine(default_lang="en")

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

    print("\n🌍 Language Mapping:")
    print("-" * 20)
    for lang, mapped_lang in gtts.LANGUAGE_MAP.items():
        print(f"{lang} → {mapped_lang}")


if __name__ == "__main__":
    main()
