<div align="center">

# TTSKit

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![FastAPI](https://img.shields.io/badge/FastAPI-enabled-success)](#)
![Telegram](https://img.shields.io/badge/Telegram-bot-blue)
![CLI](https://img.shields.io/badge/CLI-Typer-informational)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Tests](https://img.shields.io/badge/tests-2414%2F2414-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)
![Ruff](https://img.shields.io/badge/ruff-checked-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Redis](https://img.shields.io/badge/redis-optional-orange)

Python Text-to-Speech toolkit (multi-engine) with FastAPI, CLI and Telegram integration. Featuring first-class Persian support.

</div>

## ✨ Features

### 🤖 Multi-Framework Telegram Support

- **aiogram**: Modern async framework with full Telegram Bot API support
- **pyrogram**: Powerful library with advanced capabilities
- **telethon**: Fast and reliable library
- **telebot**: Simple and user-friendly library

### 🎵 Multi-Engine TTS

- **gTTS**: Google engine with high quality and 100+ language support
- **Edge TTS**: Microsoft engine with natural voice and Persian support
- **Piper TTS**: Offline engine with studio-quality output and high speed

### 🇮🇷 Persian-First Design

- **Native RTL Support**: Proper Persian text display in user interface
- **High-Quality Persian Voice**: Using Edge TTS with DilaraNeural voice
- **Automatic Language Detection**: Smart engine selection for each language
- **Persian Number Support**: Automatic conversion of English numbers to Persian

### 🚀 Production-Ready

- **Health Monitoring**: System, database, and service status checks
- **Smart Caching System**: Reduced response time and resource optimization
- **Rate Limiting**: Abuse prevention and traffic control
- **Advanced Logging**: Complete activity and error logging

### 🛡️ Security & Quality

- **Type-Safe**: Full type hints and Pydantic validation
- **Thoroughly Tested**: 2414 tests with 87% code coverage
- **Input Validation**: Complete user input sanitization and validation
- **Error Management**: Smart error handling and automatic recovery

### 🔧 Advanced Features

- **Powerful CLI**: Command-line tools for management and usage
- **RESTful API**: Programming interface for system integration
- **Docker Support**: Easy deployment with containers
- **Flexible Configuration**: Advanced settings via environment variables

## 🚀 Quick Start

### Prerequisites

```bash
# Install FFmpeg (required for audio processing)
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

### Installation & Setup

```bash
# 1. Install TTSKit
pip install .

# 2. Setup system (database, migrations, tests)
ttskit setup

# 3. Configure environment
cp .env.example .env
# Edit .env with your BOT_TOKEN

# 4. Run bot
ttskit start --token YOUR_BOT_TOKEN --framework aiogram
```

**Test in Telegram:**

```
/voice fa: سلام دنیا
/voice en: Hello world
/health
```

## 📚 Usage

### CLI Commands

```bash
# Check available commands
ttskit --help

# Synthesize text to audio
ttskit synth "سلام دنیا" --lang fa --output salam.ogg

# System health check
ttskit health --verbose

# Cache management
ttskit cache --stats
```

### Library Usage

```python
from ttskit import EngineRouter, to_opus_ogg

router = EngineRouter(default_lang="en")
engine, engine_name = router.select("fa")  # Auto-selects Edge for Persian
mp3_file = engine.synth_to_mp3("سلام دنیا", "fa")
to_opus_ogg(mp3_file, "output.ogg")
```

## 🏗️ Architecture

```
ttskit/
├── ttskit/                    # Main package
│   ├── bot/                   # Telegram bot (multi-framework)
│   ├── engines/               # TTS engines (gTTS, Edge, Piper)
│   ├── api/                   # FastAPI endpoints
│   ├── database/              # SQLAlchemy models & migrations
│   ├── telegram/              # Multi-framework adapters
│   └── utils/                 # Audio, parsing, validation utilities
├── ttskit_cli/               # CLI tools
├── tests/                    # Test suite (2414 tests, 87% coverage)
├── examples/                 # Usage examples
├── models/                   # TTS model files
│   └── piper/                # Piper TTS models
└── data/                     # User data directory
    ├── sessions/              # Telegram session files
    └── ttskit.db             # SQLite database
```

## ⚙️ Configuration

```bash
# Required
BOT_TOKEN=your_telegram_token

# TTS Configuration
DEFAULT_LANG=en
TTS_ENGINE=gtts
ENGINE_ROUTING=en:gtts,fa:edge,ar:gtts

# Edge Voice Overrides
EDGE_VOICE_en=en-US-JennyNeural
EDGE_VOICE_fa=fa-IR-DilaraNeural

# Optional Features
ENABLE_CACHING=false
ENABLE_RATE_LIMITING=false
REDIS_URL=redis://localhost:6379
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ttskit --cov-report=html

# Run specific categories
pytest tests/test_engines_*.py -v
pytest tests/test_bot_*.py -v
```

**Coverage**: 87% (8,020 statements covered out of 9,959 total)

## 🐳 Docker

```bash
# Build and run
docker build -t ttskit .
docker run --env-file .env ttskit

# With docker-compose
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run quality checks: `ruff check . && mypy ttskit && pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **aiogram**: Modern async Telegram Bot framework
- **pydub**: Audio processing and conversion
- **gTTS**: Google Text-to-Speech engine
- **edge-tts**: Microsoft Edge TTS engine
- **piper-tts**: High-quality offline TTS engine
- **Pydantic**: Data validation and settings management
- **Typer**: Modern CLI framework

## 🔧 Troubleshooting

### Common Issues

**FFmpeg not found:**

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

**Database migration fails:**

```bash
# Run setup command first
ttskit setup
```

**Bot doesn't start:**

```bash
# Check if .env file exists and has BOT_TOKEN
cat .env | grep BOT_TOKEN

# Validate configuration
ttskit config --validate
```

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/dibbed/TTSKit-multi-engine-tts/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dibbed/TTSKit-multi-engine-tts/discussions)
- **Documentation**: [Full Documentation](https://github.com/dibbed/TTSKit-multi-engine-tts#readme)

---

<div align="center">

📄 برای نسخه فارسی [کلیک کنید](README.md)

**Made with ❤️ for the Persian developer community**

</div>
