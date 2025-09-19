#!/usr/bin/env python3
"""Helper script for voices command to avoid logging issues."""

import logging
import os
import sys
import warnings

os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TTSKIT_LOG_LEVEL"] = "CRITICAL"
os.environ["PYROGRAM_LOG_LEVEL"] = "CRITICAL"
os.environ["TELETHON_LOG_LEVEL"] = "CRITICAL"
os.environ["PYDUB_LOG_LEVEL"] = "CRITICAL"

logging.basicConfig(level=logging.CRITICAL, format="")
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("ttskit").setLevel(logging.CRITICAL)
logging.getLogger("pyrogram").setLevel(logging.CRITICAL)
logging.getLogger("telethon").setLevel(logging.CRITICAL)
logging.getLogger("pydub").setLevel(logging.CRITICAL)
logging.getLogger("pyrogram.crypto").setLevel(logging.CRITICAL)
logging.getLogger("telethon.crypto").setLevel(logging.CRITICAL)
logging.getLogger("telethon.crypto.aes").setLevel(logging.CRITICAL)
logging.getLogger("telethon.crypto.libssl").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ttskit.engines.factory import EngineFactory


def main():
    """Lists available TTS voices, filtered by engine or language if provided.

    Args:
        sys.argv: Expects engine (optional, 'None' for all) and lang (optional, 'None' for all).

    Notes:
        Uses EngineFactory to create engines and list voices; prints formatted output.
        If engine specified, lists for that; else, all engines with totals.
    """
    factory = EngineFactory()
    factory._register_default_engines()

    engine = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "None" else None
    lang = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "None" else None

    if engine:
        engine_instance = factory.create_engine(engine)
        if not engine_instance:
            print(f"❌ Engine '{engine}' not found")
            sys.exit(1)

        voices = engine_instance.list_voices(lang)

        if not voices:
            print(f"No voices found for engine '{engine}'")
            sys.exit(0)

        print(f"🎵 Available voices for {engine} ({len(voices)} total):")
        print("=" * 50)

        for voice in sorted(voices):
            print(f"  • {voice}")
    else:
        available_engines = factory.get_available_engines()
        total_voices = 0

        print("🎵 Available voices by engine:")
        print("=" * 50)

        for engine_name in available_engines:
            engine_instance = factory.create_engine(engine_name)
            if engine_instance:
                engine_voices = engine_instance.list_voices(lang)

                if engine_voices:
                    print(f"\n🔧 {engine_name} ({len(engine_voices)} voices):")
                    for voice in sorted(engine_voices):
                        print(f"  • {voice}")
                    total_voices += len(engine_voices)

        print(f"\n📊 Total voices: {total_voices}")


if __name__ == "__main__":
    main()
