import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ttskit.engines.edge_engine import EdgeEngine
from ttskit.utils.audio import to_opus_ogg

VOICE_BY_LANG = {
    "fa": "fa-IR-DilaraNeural",
    "ar": "ar-SA-HamedNeural",
    "en": "en-US-JennyNeural",
}


def pick_voice(lang: str) -> str:
    """Selects appropriate voice based on language code.
    
    Args:
        lang: Language code (fa, ar, en)
        
    Returns:
        Voice name string for the specified language, defaults to English
    """
    code = (lang or "en").lower()
    return VOICE_BY_LANG.get(code, VOICE_BY_LANG["en"])


def main() -> None:
    """Command-line interface for Edge TTS synthesis with OGG/Opus output.
    
    Parses command-line arguments for text, language, and output file,
    synthesizes audio using Edge TTS engine, converts to OGG format,
    and saves the result to the specified file.
    """
    parser = argparse.ArgumentParser(
        description="Synthesize text with Edge TTS and export OGG/Opus"
    )
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument(
        "--lang", default="en", help="Language code: fa|ar|en (default: en)"
    )
    parser.add_argument("--out", default="edge_output.ogg", help="Output .ogg filename")
    args = parser.parse_args()

    voice = pick_voice(args.lang)
    engine = EdgeEngine(default_lang=args.lang, voice=voice)
    mp3_path = engine.synth_to_mp3(args.text, args.lang)
    to_opus_ogg(mp3_path, args.out)
    print(f"Saved to {args.out} (voice={voice})")


if __name__ == "__main__":
    main()
