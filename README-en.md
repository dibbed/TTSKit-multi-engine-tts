# TTSKit

TTSKit is a modular Python Text-to-Speech (TTS) toolkit and service layer. It provides unified speech synthesis across multiple engines, a multi-framework Telegram bot, a FastAPI REST API with streaming audio responses, and a Typer-powered command-line interface, featuring first-class Persian language support (RTL layout, Persian numerals, and high-fidelity neural voices).

---

## Architecture Overview

TTSKit is structured into decoupled, interchangeable layers:

```
ttskit/
├── ttskit/
│   ├── api/             # FastAPI application, streaming endpoints, auth dependencies
│   ├── bot/             # Telegram bot command routing, interactive callbacks, unified bot
│   ├── cache/           # Memory and Redis caching backends
│   ├── database/        # SQLAlchemy models, SQLite/PostgreSQL storage, key hashing
│   ├── engines/         # TTS engines (Edge TTS, Piper TTS, gTTS) and SmartRouter
│   ├── telegram/        # Multi-framework adapters (aiogram, pyrogram, telethon, telebot)
│   └── utils/           # Audio transcoding (FFmpeg), text normalization, temp file manager
├── ttskit_cli/          # Typer CLI application (`ttskit` command)
├── tests/               # Pytest suite
└── models/piper/        # Local Piper ONNX voice models and JSON configs
```

- **Engines & Routing**: Each engine (`EdgeEngine`, `PiperEngine`, `GTTSEngine`) implements `TTSEngine`. `SmartRouter` resolves candidate engines based on language policies and automatically falls back to secondary engines if the primary engine encounters a failure.
- **Unified Telegram Bot**: `UnifiedTTSBot` exposes identical bot behaviors across four different Telegram libraries through a common `TelegramAdapter` interface.
- **Audio Pipeline**: Raw audio produced by synthesis engines is transcoded via FFmpeg into Opus-encoded OGG containers (`audio/ogg; codecs=opus`) for Telegram voice notes, or exported as MP3/WAV.
- **Security & Caching**: API keys are hashed (Argon2 / bcrypt / SHA-256) and never retained in plaintext in memory objects. Synthesized audio responses are cached by cryptographic digest to minimize latency and external requests.

---

## Supported TTS Engines

| Engine | Type | Default Voices | Strengths & Notes |
|---|---|---|---|
| **Microsoft Edge TTS** (`edge`) | Cloud (online) | Persian: `fa-IR-DilaraNeural`, `fa-IR-FaridNeural`<br>English: `en-US-JennyNeural`, `en-US-GuyNeural` | Default engine. High-fidelity neural voices, natural prosody, supports dynamic rate and pitch tuning. Requires internet access. |
| **Piper TTS** (`piper`) | Local (offline) | Persian: `fa_IR-amir-medium`<br>English: `en_US-lessac-medium` | Fast, deterministic, zero-network neural TTS using ONNX runtime. Requires model files in `models/piper/`. |
| **Google Translate TTS** (`gTTS`) | Cloud (online) | Standard Google voices | Lightweight fallback engine supporting over 100 languages. Slower than Edge TTS, limited voice customization. |

---

## Telegram Framework Adapters

TTSKit supports four distinct Telegram libraries through swappable adapters:

1. **aiogram (v3)** (`aiogram`): Modern asynchronous framework, recommended default.
2. **Pyrogram** (`pyrogram`): Fast MTProto client library with async support.
3. **Telethon** (`telethon`): Mature asynchronous MTProto library.
4. **pyTelegramBotAPI** (`telebot`): Traditional synchronous/threaded library.

Select the active adapter by setting `TELEGRAM_DRIVER=aiogram` in `.env` or passing `--adapter aiogram` on the CLI.

---

## Prerequisites

- **Python**: 3.11 or higher
- **FFmpeg**: Mandatory system dependency required for Opus audio encoding and WAV/MP3 conversion
- **Redis** *(optional)*: For distributed multi-instance caching
- **SQLite / PostgreSQL** *(optional)*: For persistent user settings and API key management

### Installing FFmpeg

FFmpeg must be installed and available in your system's `PATH`:

- **Ubuntu / Debian**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

- **macOS** (Homebrew):
  ```bash
  brew install ffmpeg
  ```

- **Windows**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  *Alternatively, download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin/` directory to your system `PATH`.*

Verify the installation:
```bash
ffmpeg -version
```

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dibbed/TTSKit-multi-engine-tts.git
   cd TTSKit-multi-engine-tts
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Linux/macOS:
   source .venv/bin/activate
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

4. Initialize the system (database, migrations, and self-checks):
   ```bash
   ttskit setup
   ```

---

## Configuration Reference

TTSKit loads settings from environment variables or a `.env` file in the project root. Variables may be set without a prefix or prefixed with `TTSKIT_`.

| Variable | Type | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | string | `None` | Telegram Bot API token from [@BotFather](https://t.me/BotFather). Required for bot mode. |
| `TELEGRAM_DRIVER` | string | `aiogram` | Telegram framework driver: `aiogram`, `pyrogram`, `telethon`, or `telebot`. |
| `TELEGRAM_API_ID` | integer | `None` | Telegram API ID (required when using Pyrogram or Telethon). |
| `TELEGRAM_API_HASH` | string | `None` | Telegram API Hash (required when using Pyrogram or Telethon). |
| `DEFAULT_LANG` | string | `en` | Default synthesis language code (`fa`, `en`, `ar`, etc.). |
| `TTS_ENGINE` | string | `edge` | Default TTS engine (`edge`, `piper`, or `gtts`). |
| `TTS_POLICY_FA` | string | `edge,piper,gtts` | Engine fallback sequence for Persian (`fa`). |
| `TTS_POLICY_EN` | string | `edge,gtts,piper` | Engine fallback sequence for English (`en`). |
| `EDGE_VOICE_FA` | string | `fa-IR-DilaraNeural` | Default Edge voice for Persian. |
| `EDGE_VOICE_EN` | string | `en-US-JennyNeural` | Default Edge voice for English. |
| `PIPER_MODEL_PATH` | string | `./models/piper/` | Path to Piper ONNX models directory. |
| `PIPER_USE_CUDA` | boolean | `false` | Enable CUDA GPU acceleration for Piper. |
| `ENABLE_CACHING` | boolean | `true` | Enable synthesis caching. |
| `CACHE_TTL` | integer | `3600` | Cache time-to-live in seconds. |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Redis connection URL. Leave unset or empty to use in-memory cache. |
| `DATABASE_URL` | string | `None` | SQLAlchemy database URL (defaults to SQLite at `data/ttskit.db`). |
| `LOG_LEVEL` | string | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `MAX_TEXT_LENGTH` | integer | `1000` | Maximum character length allowed per synthesis request. |
| `ENABLE_RATE_LIMITING` | boolean | `true` | Enable rate limiting on API and bot. |
| `RATE_LIMIT_RPM` | integer | `10` | Maximum synthesis requests allowed per minute per user/key. |

---

## Command-Line Interface (`ttskit`)

TTSKit provides a Typer CLI application for synthesis, bot management, API serving, and diagnostics:

```bash
# View all available CLI commands
ttskit --help

# Synthesize text to an audio file
ttskit synth "سلام دنیا" --lang fa --engine edge --out salam.ogg
ttskit synth "Hello from TTSKit" --lang en --engine edge --rate +10% --out hello.mp3

# Start the Telegram bot
ttskit start --token YOUR_BOT_TOKEN --adapter aiogram

# Run the FastAPI REST API server
ttskit api --host 127.0.0.1 --port 8000 --reload

# List available voices (optionally filtered by engine and language)
ttskit voices --engine edge --lang fa

# Inspect system and engine capabilities
ttskit engines
ttskit info "متن آزمایشی جهت تحلیل زبان و مدت زمان صوت"

# Check system dependencies, database, and network health
ttskit health

# Inspect and manage the cache
ttskit cache --stats
ttskit cache-clear

# Initialize database and execute migrations
ttskit setup
ttskit migrate --check

# Validate configuration
ttskit config --validate
```

---

## Python SDK / Library Usage

### High-Level API

```python
from ttskit import TTS, SynthConfig

# Initialize TTS client with default language
tts = TTS(default_lang="fa")

# Synchronous synthesis
config = SynthConfig(
    text="سلام، به کیت صوتی خوش آمدید.",
    lang="fa",
    engine="edge",
    output_format="ogg"
)
audio = tts.synth_sync(config)
audio.save("output.ogg")
```

### Asynchronous Synthesis

```python
import asyncio
from ttskit import TTS, SynthConfig

async def main():
    tts = TTS(default_lang="en")
    config = SynthConfig(
        text="TTSKit provides asynchronous, non-blocking synthesis.",
        lang="en",
        rate=1.1,
        output_format="mp3"
    )
    audio = await tts.synth_async(config)
    audio.save("async_output.mp3")

asyncio.run(main())
```

### Direct SmartRouter & Audio Conversion

```python
import asyncio
from ttskit import SmartRouter, to_opus_ogg

async def synthesize_and_convert():
    router = SmartRouter()
    
    # Synthesizes using best engine with automatic fallback
    audio_bytes, engine_used = await router.synth_async("Hello world", lang="en")
    print(f"Synthesized {len(audio_bytes)} bytes using {engine_used}")
    
    # Convert arbitrary audio files to Telegram-compliant Opus OGG
    to_opus_ogg("input.wav", "voice_note.ogg")

asyncio.run(synthesize_and_convert())
```

---

## REST API

Start the REST API server:
```bash
ttskit api --host 0.0.0.0 --port 8000
```
Interactive documentation is available at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc`.

### Endpoints

- `POST /api/v1/synth`: Synthesize text and return audio as a streaming response.
- `POST /api/v1/synth/batch`: Batch synthesis for multiple texts.
- `GET /api/v1/engines`: List all registered engines and their availability.
- `GET /api/v1/voices`: List available voices, filterable by engine and language.
- `GET /health`: Public health check endpoint returning engine count, uptime, and service status.

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/synth \
  -H "Content-Type: application/json" \
  -d '{
    "text": "سلام دنیا، سرویس ای‌پی‌آی آماده است.",
    "lang": "fa",
    "engine": "edge",
    "voice": "fa-IR-DilaraNeural",
    "rate": 1.0,
    "pitch": 0.0,
    "format": "ogg"
  }' \
  --output response.ogg
```

---

## Telegram Bot

### Starting the Bot

Set `BOT_TOKEN` in `.env` or pass `--token`:

```bash
ttskit start --token "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" --adapter aiogram
```

### Supported Commands

| Command | Usage | Description |
|---|---|---|
| `/start` | `/start` | Welcome message, user registration, and language selection. |
| `/help` | `/help` | Detailed command list and usage guide. |
| `/voice` | `/voice fa: متن شما` or `/voice Hello` | Converts the provided text to a voice note. Language prefix is optional. |
| `/engine` | `/engine edge` | Switches user's preferred TTS engine (`edge`, `piper`, `gtts`). |
| `/lang` | `/lang fa` | Sets user's default language. |
| `/rate` | `/rate 1.2` | Sets speech speed multiplier (0.5 to 2.0). |
| `/pitch` | `/pitch +2` | Adjusts speech pitch in semitones (-12 to +12). |
| `/settings` | `/settings` | Displays interactive inline keyboard for changing voice, speed, and engine. |
| `/stats` | `/stats` | Shows user or bot synthesis statistics. |
| `/health` | `/health` | Diagnostic status report of all subsystems. |
| Inline Mode | `@YourBot سلام` | Generates voice notes inline within any Telegram chat. |

---

## Piper TTS Setup (Offline Mode)

Piper enables 100% offline, local neural speech synthesis using ONNX runtime:

1. Create the Piper models directory:
   ```bash
   mkdir -p models/piper
   ```

2. Download your desired voice model (`.onnx`) and its corresponding JSON config (`.onnx.json`).
   - For Persian:
     - Model: `fa_IR-amir-medium.onnx`
     - Config: `fa_IR-amir-medium.onnx.json`
   - For English:
     - Model: `en_US-lessac-medium.onnx`
     - Config: `en_US-lessac-medium.onnx.json`

3. Place both files in `models/piper/`:
   ```
   models/piper/
   ├── fa_IR-amir-medium.onnx
   ├── fa_IR-amir-medium.onnx.json
   ├── en_US-lessac-medium.onnx
   └── en_US-lessac-medium.onnx.json
   ```

4. Enable Piper in `.env`:
   ```bash
   TTS_ENGINE=piper
   PIPER_ENABLED=true
   PIPER_MODEL_PATH=./models/piper/
   ```

---

## Database & Security

- **Database Initialization**: Run `ttskit setup` to create tables and initialize SQLite (default: `data/ttskit.db`).
- **Cryptographic Key Storage**: API keys are securely hashed using modern cryptographic algorithms (Argon2 / bcrypt / SHA-256 fallback) prior to persistence. Plaintext secret keys are never retained in memory objects (`APIKeyAuth.api_key is None`), preventing credential leakage through logging or state inspection.
- **Migrations**: Database schema updates are applied safely using `ttskit migrate`.

---

## Testing & Quality Assurance

Run the test suite and static analysis tools locally:

```bash
# Execute full test suite
pytest tests -q

# Run with test coverage report
pytest --cov=ttskit --cov-report=term-missing

# Linting and style verification
ruff check .

# Static type checking
mypy ttskit ttskit_cli
```

---

## Production Considerations & Limitations

1. **Network Connectivity**: Edge TTS and gTTS require stable outbound HTTP/HTTPS connectivity to Microsoft and Google servers. For isolated or zero-network environments, configure Piper TTS with local models.
2. **FFmpeg Availability**: Conversion to Telegram-compatible Opus OGG voice notes depends on the FFmpeg binary. Ensure FFmpeg is present in system `$PATH` and has read/write access to temporary directories.
3. **Caching Strategy**: The default in-memory cache is suitable for single-process setups. In multi-worker or containerized deployments, set `REDIS_URL` to ensure consistent cache sharing across processes.
4. **Hardware Acceleration**: Piper inference defaults to CPU. For high-throughput offline synthesis on compatible systems, enable `PIPER_USE_CUDA=true`.
