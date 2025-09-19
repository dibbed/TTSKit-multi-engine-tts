#!/usr/bin/env python3
"""
Script to generate README.md dynamically
"""

from ttskit.engines.factory import factory
from ttskit.public import TTS
from ttskit.version import __version__


def main():
    # Get engine information
    engines = factory.get_available_engines()
    tts = TTS()
    supported_languages = tts.get_supported_languages()

    # Generate README content
    readme_content = f"""# TTSKit

A powerful, multi-engine Text-to-Speech (TTS) library and bot framework for Python.

## Features

- **Multi-Engine Support**: Edge TTS, Google TTS, Piper TTS
- **Smart Routing**: Automatic engine selection based on language and performance
- **Caching**: Redis and memory caching for improved performance
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **Multi-Framework**: Support for aiogram, pyrogram, telethon, and pyTelegramBotAPI
- **REST API**: FastAPI-based REST API for easy integration
- **Internationalization**: Support for multiple languages including Persian, English, and Arabic

## Installation

```bash
pip install ttskit
```

## Quick Start

### Basic Usage

```python
from ttskit import TTS

# Initialize TTS
tts = TTS()

# Synthesize text
audio = tts.synth('Hello, World!', lang='en')
```

### Bot Usage

```python
from ttskit.bot.unified_bot import UnifiedTTSBot

# Create bot
bot = UnifiedTTSBot(
    bot_token='YOUR_BOT_TOKEN',
    adapter_type='aiogram'
)

# Start bot
await bot.start()
```

### API Usage

```python
from ttskit.api.app import app
import uvicorn

# Start API server
uvicorn.run(app, host='0.0.0.0', port=8080)
```

## Supported Languages

{", ".join(supported_languages)}

## Available Engines

{", ".join(engines)}

## Version

{__version__}

## Documentation

For detailed documentation, visit [https://ttskit.dev](https://ttskit.dev)

## License

MIT License

## Contributing

Contributions are welcome! Please read our contributing guidelines.

## Support

For support, please open an issue on GitHub.
"""

    # Write README
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("✅ README updated successfully")


if __name__ == "__main__":
    main()
