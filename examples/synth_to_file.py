import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ttskit.engines.gtts_engine import GTTSEngine
from ttskit.utils.audio import to_opus_ogg


def main() -> None:
    """Command-line interface for Google TTS synthesis with OGG/Opus output.
    
    Parses command-line arguments for text, language, and output file,
    synthesizes audio using Google TTS engine, converts to OGG format,
    and saves the result to the specified file.
    """
    parser = argparse.ArgumentParser(
        description="Synthesize text to OGG/Opus using gTTS"
    )
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument("--out", default="output.ogg", help="Output .ogg filename")
    args = parser.parse_args()

    engine = GTTSEngine(default_lang=args.lang)
    mp3_path = engine.synth_to_mp3(args.text, args.lang)
    to_opus_ogg(mp3_path, args.out)
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
