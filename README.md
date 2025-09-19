<div align="center">

# TTSKit

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![FastAPI](https://img.shields.io/badge/FastAPI-enabled-success)](#)
![Telegram](https://img.shields.io/badge/Telegram-bot-blue)
![CLI](https://img.shields.io/badge/CLI-Typer-informational)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Tests](https://img.shields.io/badge/tests-2414%2F2414-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Redis](https://img.shields.io/badge/redis-optional-orange)

یک کیت متن‌به‌گفتار (TTS) چند موتوره برای پایتون با پشتیبانی از FastAPI، خط فرمان و تلگرام. دارای پشتیبانی ویژه از زبان فارسی.

</div>

## ✨ ویژگی‌ها

### 🤖 چندفریمورک تلگرام

- **aiogram**: فریمورک مدرن async با پشتیبانی کامل از Telegram Bot API
- **pyrogram**: کتابخانه قدرتمند با قابلیت‌های پیشرفته
- **telethon**: کتابخانه سریع و قابل اعتماد
- **telebot**: کتابخانه ساده و کاربردی

### 🎵 چندموتور TTS

- **gTTS**: موتور Google با کیفیت بالا و پشتیبانی از 100+ زبان
- **Edge TTS**: موتور Microsoft با صدای طبیعی و پشتیبانی از فارسی
- **Piper TTS**: موتور آفلاین با کیفیت استودیویی و سرعت بالا

### 🇮🇷 اولویت فارسی

- **پشتیبانی بومی RTL**: نمایش صحیح متن فارسی در رابط کاربری
- **صدای فارسی باکیفیت**: استفاده از Edge TTS با صدای DilaraNeural
- **تشخیص خودکار زبان**: انتخاب خودکار موتور مناسب برای هر زبان
- **پشتیبانی از اعداد فارسی**: تبدیل خودکار اعداد انگلیسی به فارسی

### 🚀 آماده تولید

- **مانیتورینگ سلامت**: بررسی وضعیت سیستم، دیتابیس و سرویس‌ها
- **سیستم کش هوشمند**: کاهش زمان پاسخ و صرفه‌جویی در منابع
- **محدودیت نرخ**: جلوگیری از سوءاستفاده و کنترل ترافیک
- **لاگ‌گیری پیشرفته**: ثبت کامل فعالیت‌ها و خطاها

### 🛡️ امنیت و کیفیت

- **نوع‌ایمن**: Type hints کامل و اعتبارسنجی Pydantic
- **تست شده**: 2414 تست با 87% پوشش کد
- **اعتبارسنجی ورودی**: بررسی و پاکسازی تمام ورودی‌های کاربر
- **مدیریت خطا**: مدیریت هوشمند خطاها و بازیابی خودکار

### 🔧 قابلیت‌های پیشرفته

- **CLI قدرتمند**: ابزارهای خط فرمان برای مدیریت و استفاده
- **API RESTful**: رابط برنامه‌نویسی برای ادغام با سیستم‌های دیگر
- **پشتیبانی Docker**: راه‌اندازی آسان با کانتینر
- **پیکربندی انعطاف‌پذیر**: تنظیمات پیشرفته از طریق متغیرهای محیطی

## 🚀 شروع سریع

### پیش‌نیازها

```bash
# نصب FFmpeg (الزامی برای پردازش صوتی)
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: از https://ffmpeg.org/download.html دانلود کنید
```

### نصب و راه‌اندازی

```bash
# 1. نصب TTSKit
pip install .

# 2. راه‌اندازی سیستم (دیتابیس، migration، تست)
ttskit setup

# 3. پیکربندی محیط
cp .env.example .env
# ویرایش .env با BOT_TOKEN

# 4. اجرای ربات
ttskit start --token YOUR_BOT_TOKEN --framework aiogram
```

**تست در تلگرام:**

```
/voice fa: سلام دنیا
/voice en: Hello world
/health
```

## 📚 استفاده

### دستورات CLI

```bash
# بررسی دستورات موجود
ttskit --help

# تبدیل متن به صدا
ttskit synth "سلام دنیا" --lang fa --output salam.ogg

# بررسی سلامت سیستم
ttskit health --verbose

# مدیریت کش
ttskit cache --stats
```

### استفاده از کتابخانه

```python
from ttskit import EngineRouter, to_opus_ogg

router = EngineRouter(default_lang="en")
engine, engine_name = router.select("fa")  # خودکار Edge برای فارسی انتخاب می‌کند
mp3_file = engine.synth_to_mp3("سلام دنیا", "fa")
to_opus_ogg(mp3_file, "output.ogg")
```

## 🏗️ معماری

```
ttskit/
├── ttskit/                    # بسته اصلی
│   ├── bot/                   # ربات تلگرام (چندفریمورک)
│   ├── engines/               # موتورهای TTS (gTTS, Edge, Piper)
│   ├── api/                   # endpointهای FastAPI
│   ├── database/              # مدل‌های SQLAlchemy و migrationها
│   ├── telegram/              # آداپترهای چندفریمورک
│   └── utils/                 # ابزارهای صوتی، تجزیه، اعتبارسنجی
├── ttskit_cli/               # ابزارهای CLI
├── tests/                    # مجموعه تست (2414 تست، 87% پوشش)
├── examples/                 # مثال‌های استفاده
├── models/                   # فایل‌های مدل TTS
│   └── piper/                # مدل‌های Piper TTS
└── data/                     # دایرکتوری داده‌های کاربر
    ├── sessions/              # فایل‌های session تلگرام
    └── ttskit.db             # دیتابیس SQLite
```

## ⚙️ پیکربندی

```bash
# الزامی
BOT_TOKEN=your_telegram_token

# پیکربندی TTS
DEFAULT_LANG=en
TTS_ENGINE=edge
ENGINE_ROUTING=en:edge,fa:edge,ar:edge

# Override صدای Edge
EDGE_VOICE_en=en-US-JennyNeural
EDGE_VOICE_fa=fa-IR-DilaraNeural

# ویژگی‌های اختیاری
ENABLE_CACHING=true
ENABLE_RATE_LIMITING=true
REDIS_URL=redis://localhost:6379
```

## 🧪 تست

```bash
# اجرای همه تست‌ها
pytest

# اجرا با پوشش
pytest --cov=ttskit --cov-report=html

# اجرای دسته‌های خاص
pytest tests/test_engines_*.py -v
pytest tests/test_bot_*.py -v
```

**پوشش**: 87% (8,020 عبارت پوشش داده شده از 9,959 کل)

## 🐳 داکر

```bash
# ساخت و اجرا
docker build -t ttskit .
docker run --env-file .env ttskit

# با docker-compose
docker-compose up -d
```

## 🤝 مشارکت

1. مخزن را fork کنید
2. شاخه ویژگی ایجاد کنید: `git checkout -b feature/amazing-feature`
3. تغییرات خود را اعمال کنید و تست اضافه کنید
4. بررسی‌های کیفیت اجرا کنید: `ruff check . && mypy ttskit && pytest`
5. تغییرات را commit کنید: `git commit -m 'Add amazing feature'`
6. به شاخه push کنید: `git push origin feature/amazing-feature`
7. Pull Request باز کنید

## 📄 مجوز

این پروژه تحت مجوز MIT مجوزدهی شده است - فایل [LICENSE](LICENSE) را برای جزئیات ببینید.

## 🙏 تشکر

- **aiogram**: فریمورک مدرن async ربات تلگرام
- **pydub**: پردازش و تبدیل صوتی
- **gTTS**: موتور Google Text-to-Speech
- **edge-tts**: موتور Microsoft Edge TTS
- **Pydantic**: اعتبارسنجی داده و مدیریت تنظیمات
- **Typer**: فریمورک مدرن CLI

## 🔧 عیب‌یابی

### مشکلات رایج

**FFmpeg پیدا نشد:**

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: از https://ffmpeg.org/download.html دانلود کنید
```

**Migration دیتابیس ناموفق:**

```bash
# ابتدا دستور setup را اجرا کنید
ttskit setup
```

**ربات شروع نمی‌شود:**

```bash
# بررسی وجود فایل .env و BOT_TOKEN
cat .env | grep BOT_TOKEN

# اعتبارسنجی پیکربندی
ttskit config --validate
```

## 📞 پشتیبانی

- **Issues**: [GitHub Issues](https://github.com/dibbed/TTSKit-multi-engine-tts/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dibbed/TTSKit-multi-engine-tts/discussions)
- **مستندات**: [مستندات کامل](https://github.com/dibbed/TTSKit-multi-engine-tts#readme)

---

<div align="center">

📄 For English version [click here](README-en.md)

**ساخته شده با ❤️ برای جامعه توسعه‌دهندگان فارسی‌زبان**

</div>
