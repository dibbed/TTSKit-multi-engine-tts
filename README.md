# TTSKit

کیت متن‌به‌گفتار (Text-to-Speech) ماژولار و حرفه‌ای برای پایتون با پشتیبانی از چندین موتور سنتز صوت، ربات تلگرام چندفریمورکه، رابط برنامه‌نویسی RESTful بر پایه FastAPI، و خط فرمان قدرتمند بر پایه Typer. این پروژه با تمرکز ویژه بر پردازش و تولید صدای طبیعی برای زبان فارسی (راست‌به‌چپ، صدای عصبی باکیفیت و پردازش اعداد) توسعه یافته است.

---

## ساختار و معماری پروژه

معماری TTSKit به صورت لایه‌ای و مستقل از وابستگی‌های متقابل طراحی شده است:

```
ttskit/
├── ttskit/
│   ├── api/             # برنامه FastAPI، اندپوینت‌های استریمینگ و کنترل دسترسی
│   ├── bot/             # منطق ربات تلگرام، مدیریت دستورات، کیبوردهای تعاملی
│   ├── cache/           # لایه کش در حافظه (Memory) و کش توزیع‌شده (Redis)
│   ├── database/        # مدل‌های SQLAlchemy، دیتابیس SQLite/PostgreSQL و هش کلیدها
│   ├── engines/         # موتورهای سنتز صوت (Edge TTS, Piper TTS, gTTS) و SmartRouter
│   ├── telegram/        # آداپترهای فریمورک‌های مختلف تلگرام (aiogram, pyrogram, telethon, telebot)
│   └── utils/           # تبدیل و ترنسکدینگ صوت (FFmpeg)، نرمال‌سازی متن، مدیریت فایل‌های موقت
├── ttskit_cli/          # رابط خط فرمان مستقل (`ttskit`)
├── tests/               # مجموعه آزمون‌های واحد و یکپارچه‌سازی (Pytest)
└── models/piper/        # فایل‌های مدل ONNX و تنظیمات محلی Piper TTS
```

- **موتورها و مسیریابی هوشمند (`SmartRouter`)**: هر موتور کلاس پایه `TTSEngine` را پیاده‌سازی می‌کند. سیستم `SmartRouter` بر اساس سیاست‌های زبانی و نیازمندی‌های ورودی بهترین موتور را انتخاب کرده و در صورت بروز خطا در موتور اصلی، به صورت خودکار عملیات تبدیل را با موتورهای جایگزین (Fallback) ادامه می‌دهد.
- **ربات چندفریمورکه تلگرام**: کلاس `UnifiedTTSBot` منطق کسب‌وکار یکسانی را از طریق آداپترهای متصل به کتابخانه‌های مختلف تلگرام اجرا می‌کند.
- **خط لوله صوتی (Audio Pipeline)**: فایل‌های صوتی تولیدی از طریق باینری FFmpeg به فرمت استاندارد ویس تلگرام (`audio/ogg; codecs=opus`) یا فرمت‌های متداول دیگر (MP3 و WAV) تبدیل می‌شوند.
- **امنیت و محرمانگی**: کلیدهای API با الگوریتم‌های مدرن رمزنگاری (Argon2 / bcrypt / SHA-256) هش شده و هرگز به صورت متن خام در آبجکت‌های حافظه برنامه نگهداری نمی‌شوند.

---

## موتورهای تبدیل متن به گفتار پشتیبانی‌شده

| موتور | نوع | صداهای پیش‌فرض | ویژگی‌ها و ملاحظات |
|---|---|---|---|
| **Microsoft Edge TTS** (`edge`) | ابری (آنلاین) | فارسی: `fa-IR-DilaraNeural` و `fa-IR-FaridNeural`<br>انگلیسی: `en-US-JennyNeural` و `en-US-GuyNeural` | موتور پیش‌فرض پروژه. کیفیت استودیویی و بسیار طبیعی، پشتیبانی از تغییر سرعت و زیروبم، نیاز به دسترسی اینترنت. |
| **Piper TTS** (`piper`) | محلی (آفلاین) | فارسی: `fa_IR-amir-medium`<br>انگلیسی: `en_US-lessac-medium` | سریع، سبک، کاملاً آفلاین و بدون نیاز به اینترنت با موتور اجرایی ONNX. نیاز به دانلود مدل‌های محلی در مسیر `models/piper/`. |
| **Google Translate TTS** (`gTTS`) | ابری (آنلاین) | صداهای پیش‌فرض سرویس گوگل | موتور پشتیبان سبک با پوشش بیش از ۱۰۰ زبان. سرعت کمتر و شخصی‌سازی صوتی محدودتر در مقایسه با Edge. |

---

## آداپترهای فریمورک‌های تلگرام

TTSKit از ۴ فریمورک مختلف تلگرام پشتیبانی می‌کند و کاربر می‌تواند بر اساس نیازمندی زیرساخت خود درایور مناسب را انتخاب کند:

1. **aiogram (v3)** (`aiogram`): فریمورک مدرن و غیرهمگام (Async)، گزینه پیش‌فرض و پیشنهادی.
2. **Pyrogram** (`pyrogram`): کلاینت بر پایه پروتکل MTProto با سرعت بالا.
3. **Telethon** (`telethon`): کتابخانه باسابقه و پایدار بر پایه MTProto.
4. **pyTelegramBotAPI** (`telebot`): کتابخانه سنتی و پرکاربرد مبتنی بر پردازش همگام یا Threaded.

تعیین درایور از طریق گزینه `--adapter` در خط فرمان یا متغیر `TELEGRAM_DRIVER` در فایل `.env` صورت می‌گیرد.

---

## پیش‌نیازها

- **پایتون**: نسخه ۳.۱۱ یا بالاتر
- **FFmpeg**: ابزار سیستمی الزامی جهت پردازش و انکود صوت با کدک Opus
- **Redis** *(اختیاری)*: جهت اشتراک‌گذاری کش بین چند پردازه یا چند کانتینر
- **SQLite / PostgreSQL** *(اختیاری)*: جهت ذخیره‌سازی نشست‌ها و مدیریت کلیدهای API

### نصب FFmpeg

وجود ابزار `ffmpeg` در متغیر مسیر سیستم (`PATH`) برای ایجاد ویس‌های تلگرام الزامی است:

- **اوبونتو / دبیان**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

- **مک (Homebrew)**:
  ```bash
  brew install ffmpeg
  ```

- **ویندوز**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  *یا دانلود فایل باینری از [ffmpeg.org](https://ffmpeg.org/download.html) و افزودن مسیر پوشه `bin` به `PATH` سیستم.*

بررسی صحت نصب:
```bash
ffmpeg -version
```

---

## نصب و راه‌اندازی

۱. دریافت مخزن پروژه:
   ```bash
   git clone https://github.com/dibbed/TTSKit-multi-engine-tts.git
   cd TTSKit-multi-engine-tts
   ```

۲. ایجاد و فعال‌سازی محیط مجازی پایتون:
   ```bash
   python -m venv .venv
   # لینوکس و مک:
   source .venv/bin/activate
   # ویندوز (PowerShell):
   .\.venv\Scripts\Activate.ps1
   ```

۳. نصب پکیج در حالت توسعه:
   ```bash
   pip install -e .
   ```

۴. مقداردهی اولیه سیستم، دیتابیس و اجرای بررسی‌های خودکار:
   ```bash
   ttskit setup
   ```

---

## تنظیمات و متغیرهای محیطی (`.env`)

تنظیمات برنامه از طریق متغیرهای محیطی سیستم یا فایل `.env` بارگذاری می‌شوند. متغیرها بدون پیشوند یا با پیشوند `TTSKIT_` قابل تعریف هستند:

| متغیر | نوع داده | مقدار پیش‌فرض | شرح |
|---|---|---|---|
| `BOT_TOKEN` | رشته | `None` | توکن ربات تلگرام دریافتی از [@BotFather](https://t.me/BotFather). الزامی برای اجرای ربات. |
| `TELEGRAM_DRIVER` | رشته | `aiogram` | فریمورک ربات تلگرام: `aiogram`, `pyrogram`, `telethon` یا `telebot`. |
| `TELEGRAM_API_ID` | عدد | `None` | شناسه API تلگرام (الزامی در صورت استفاده از Pyrogram یا Telethon). |
| `TELEGRAM_API_HASH` | رشته | `None` | کلید هش API تلگرام (الزامی در صورت استفاده از Pyrogram یا Telethon). |
| `DEFAULT_LANG` | رشته | `en` | زبان پیش‌فرض سنتز صوت (`fa`, `en`, `ar` و غیره). |
| `TTS_ENGINE` | رشته | `edge` | موتور پیش‌فرض تبدیل متن به گفتار (`edge`, `piper` یا `gtts`). |
| `TTS_POLICY_FA` | رشته | `edge,piper,gtts` | اولویت و ترتیب موتورهای پشتیبان برای زبان فارسی (`fa`). |
| `TTS_POLICY_EN` | رشته | `edge,gtts,piper` | اولویت و ترتیب موتورهای پشتیبان برای زبان انگلیسی (`en`). |
| `EDGE_VOICE_FA` | رشته | `fa-IR-DilaraNeural` | صدای پیش‌فرض موتور Edge برای زبان فارسی. |
| `EDGE_VOICE_EN` | رشته | `en-US-JennyNeural` | صدای پیش‌فرض موتور Edge برای زبان انگلیسی. |
| `PIPER_MODEL_PATH` | رشته | `./models/piper/` | مسیر پوشه فایل‌های مدل ONNX برای موتور Piper. |
| `PIPER_USE_CUDA` | بولی | `false` | استفاده از شتاب‌دهنده گرافیکی CUDA برای موتور Piper. |
| `ENABLE_CACHING` | بولی | `true` | فعال بودن کش فایل‌های صوتی تولید شده. |
| `CACHE_TTL` | عدد | `3600` | مدت اعتبار فایل‌های کش به ثانیه. |
| `REDIS_URL` | رشته | `redis://localhost:6379/0` | آدرس اتصال به ردیس. در صورت خالی بودن از حافظه موقت رم استفاده می‌شود. |
| `DATABASE_URL` | رشته | `None` | آدرس اتصال به پایگاه داده SQLAlchemy (پیش‌فرض: فایل SQLite در `data/ttskit.db`). |
| `LOG_LEVEL` | رشته | `INFO` | سطح ثبت لاگ‌ها: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `MAX_TEXT_LENGTH` | عدد | `1000` | حداکثر طول مجاز متن بر حسب تعداد کاراکتر برای هر درخواست. |
| `ENABLE_RATE_LIMITING` | بولی | `true` | فعال‌سازی سیستم محدودیت نرخ درخواست (Rate Limiting). |
| `RATE_LIMIT_RPM` | عدد | `10` | سقف تعداد درخواست مجاز در هر دقیقه برای هر کاربر یا کلید. |

---

## دستورات رابط خط فرمان (`ttskit`)

رابط خط فرمان TTSKit ابزارهای کاملی برای تبدیل متن، راه‌اندازی ربات، سرور API و مدیریت کش ارائه می‌دهد:

```bash
# مشاهده راهنما و تمام دستورات موجود
ttskit --help

# تبدیل متن فارسی به فایل صوتی
ttskit synth "سلام دنیا" --lang fa --engine edge --out salam.ogg
ttskit synth "Hello world" --lang en --engine edge --rate +10% --out hello.mp3

# راه‌اندازی ربات تلگرام
ttskit start --token YOUR_BOT_TOKEN --adapter aiogram

# راه‌اندازی سرور وب FastAPI
ttskit api --host 127.0.0.1 --port 8000 --reload

# فهرست صداهای در دسترس بر اساس موتور و زبان
ttskit voices --engine edge --lang fa

# بررسی مشخصات سیستم و ظرفیت موتورها
ttskit engines
ttskit info "متن آزمایشی جهت تحلیل زبان، کلمات و تخمین زمان تولید صوت"

# تست و ارزیابی سلامت سرویس‌ها، ارتباطات شبکه و دیتابیس
ttskit health

# مشاهده آمار و پاکسازی کش
ttskit cache --stats
ttskit cache-clear

# راه‌اندازی دیتابیس و اجرای مهاجرت‌ها
ttskit setup
ttskit migrate --check

# اعتبارسنجی تنظیمات جاری
ttskit config --validate
```

---

## استفاده از کتابخانه در کدهای پایتون

### استفاده مستقیم و همگام

```python
from ttskit import TTS, SynthConfig

# مقداردهی کلاینت با زبان پیش‌فرض فارسی
tts = TTS(default_lang="fa")

# تعریف پارامترهای تبدیل متن به صوت
config = SynthConfig(
    text="سلام، این یک پیام صوتی آزمایشی است.",
    lang="fa",
    engine="edge",
    output_format="ogg"
)

# تبدیل و ذخیره خروجی
audio = tts.synth_sync(config)
audio.save("output.ogg")
```

### تبدیل متن به صورت غیرهمگام (Async)

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

### استفاده مستقیم از مسیریاب هوشمند و ترنسکدینگ

```python
import asyncio
from ttskit import SmartRouter, to_opus_ogg

async def process_audio():
    router = SmartRouter()
    
    # تولید صوت با بهترین موتور در دسترس به همراه مدیریت خطای خودکار
    audio_bytes, engine_used = await router.synth_async("سلام بر همگی", lang="fa")
    print(f"تولید شد با موتور {engine_used}، اندازه: {len(audio_bytes)} بایت")
    
    # تبدیل فایل صوتی متفرقه به ویس استاندارد تلگرام (Opus OGG)
    to_opus_ogg("input.wav", "telegram_voice.ogg")

asyncio.run(process_audio())
```

---

## رابط برنامه‌نویسی وب (FastAPI REST API)

جهت اجرای سرور REST API دستور زیر را وارد نمایید:
```bash
ttskit api --host 0.0.0.0 --port 8000
```
مستندات تعاملی Swagger به صورت خودکار در آدرس `http://localhost:8000/docs` و مستندات ReDoc در `http://localhost:8000/redoc` در دسترس خواهند بود.

### مسیرهای اصلی (Endpoints)

- `POST /api/v1/synth`: دریافت متن و استریم مستقیم فایل صوتی تولیدی.
- `POST /api/v1/synth/batch`: تبدیل دسته‌ای چندین متن به صوت به صورت همزمان.
- `GET /api/v1/engines`: دریافت فهرست موتورهای ثبت‌شده و وضعیت آمادگی آن‌ها.
- `GET /api/v1/voices`: فهرست صداهای پشتیبانی‌شده با فیلتر زبان و موتور.
- `GET /health`: ارزیابی عمومی سلامت سرویس، تعداد موتورها و زمان آپ‌تایم.

### نمونه ارسال درخواست با `curl`

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

## ربات تلگرام

### راه‌اندازی ربات

توکن ربات را در فایل `.env` قرار دهید یا با فلگ `--token` اجرا کنید:

```bash
ttskit start --token "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" --adapter aiogram
```

### دستورات پشتیبانی‌شده در ربات

| دستور | نحوه ارسال | شرح عملکرد |
|---|---|---|
| `/start` | `/start` | پیام خوش‌آمدگویی، ثبت‌نام کاربر و انتخاب زبان اولیه. |
| `/help` | `/help` | راهنمای کامل دستورات و کلیدهای ربات. |
| `/voice` | `/voice fa: متن شما` یا `/voice متن دلخواه` | تبدیل مستقیم متن به پیام صوتی (ویس نوت). پیشوند زبان اختیاری است. |
| `/engine` | `/engine edge` | تغییر موتور فعال کاربر بین گزینه‌های `edge`, `piper` و `gtts`. |
| `/lang` | `/lang fa` | تغییر زبان پیش‌فرض کاربر. |
| `/rate` | `/rate 1.2` | تنظیم ضریب سرعت خواندن متن (بین 0.5 تا 2.0). |
| `/pitch` | `/pitch +2` | تنظیم گام صدا بر حسب نیم‌پرده (بین -12 تا +12). |
| `/settings` | `/settings` | نمایش کیبورد شیشه‌ای تنظیمات برای انتخاب صدا، سرعت و موتور. |
| `/stats` | `/stats` | مشاهده آمار استفاده کاربر یا آمار کلی سیستم. |
| `/health` | `/health` | گزارش تشخیصی سلامت بخش‌های مختلف سرویس. |
| جستجوی اینلاین | `@YourBot سلام دنیا` | تولید و ارسال مستقیم صوت در هر چت یا گروه به صورت اینلاین. |

---

## راه‌اندازی موتور محلی و آفلاین Piper TTS

موتور Piper امکان سنتز صدا به صورت ۱۰۰٪ آفلاین و محلی را با استفاده از مدل‌های سبک ONNX فراهم می‌سازد:

۱. ایجاد پوشه مدل‌ها در مسیر پروژه:
   ```bash
   mkdir -p models/piper
   ```

۲. دانلود مدل زبان مورد نظر (`.onnx`) و فایل تنظیمات ساختاری آن (`.onnx.json`):
   - برای زبان فارسی:
     - مدل: `fa_IR-amir-medium.onnx`
     - تنظیمات: `fa_IR-amir-medium.onnx.json`
   - برای زبان انگلیسی:
     - مدل: `en_US-lessac-medium.onnx`
     - تنظیمات: `en_US-lessac-medium.onnx.json`

۳. قرار دادن فایل‌ها در مسیر `models/piper/`:
   ```
   models/piper/
   ├── fa_IR-amir-medium.onnx
   ├── fa_IR-amir-medium.onnx.json
   ├── en_US-lessac-medium.onnx
   └── en_US-lessac-medium.onnx.json
   ```

۴. فعال‌سازی موتور در فایل `.env`:
   ```bash
   TTS_ENGINE=piper
   PIPER_ENABLED=true
   PIPER_MODEL_PATH=./models/piper/
   ```

---

## پایگاه داده و مدیریت امنیت کلیدها

- **مقداردهی پایگاه داده**: با اجرای دستور `ttskit setup` جداول مورد نیاز در دیتابیس SQLite (مسیر پیش‌فرض `data/ttskit.db`) ساخته می‌شوند.
- **امنیت کلیدهای دسترسی**: کلیدهای API قبل از ثبت در پایگاه داده با استفاده از الگوریتم‌های مدرن (Argon2 / bcrypt و در نبود آنها SHA-256 دارای نمک امن) هش می‌شوند. متن خام کلیدها در حافظه برنامه یا آبجکت احراز هویت ذخیره نمی‌شود (`APIKeyAuth.api_key is None`) تا از خطر افشای ناخواسته در لاگ‌ها جلوگیری شود.
- **مهاجرت طرح پایگاه داده**: به‌روزرسانی ساختار دیتابیس از طریق دستور `ttskit migrate` صورت می‌پذیرد.

---

## ارزیابی و تضمین کیفیت کد

اجرای آزمون‌ها و اعتبارسنجی کیفیت کد در محیط توسعه:

```bash
# اجرای کل آزمون‌های پروژه
pytest tests -q

# ارزیابی پوشش کد (Coverage)
pytest --cov=ttskit --cov-report=term-missing

# بررسی سبک و کیفیت کد با Ruff
ruff check .

# بررسی سازگاری انواع داده‌ها با Mypy
mypy ttskit ttskit_cli
```

---

## نکات استقرار در محیط پروداکشن و محدودیت‌ها

۱. **ارتباط شبکه**: موتورهای ابری Edge TTS و gTTS نیازمند اتصال پایدار اینترنت به سرورهای مایکروسافت و گوگل هستند. برای محیط‌های ایزوله، از موتور آفلاین Piper استفاده کنید.
۲. **حضور FFmpeg**: فرآیند تبدیل به ویس نوت تلگرام وابسته به پردازش FFmpeg است. اطمینان حاصل کنید که دسترسی اجرایی به باینری FFmpeg و نوشتن در مسیر فایل‌های موقت برقرار باشد.
۳. **کش توزیع‌شده**: برای استقرار چند کانتینری یا اجرای چندین ورکر در سرور وب، تنظیم متغیر `REDIS_URL` جهت یکپارچگی کش پیشنهاد می‌شود.
۴. **شتاب‌دهنده گرافیکی**: فرآیند سنتز صوت Piper به صورت پیش‌فرض روی CPU اجرا می‌شود. در صورت وجود کارت گرافیک انویدیا با فعال‌سازی `PIPER_USE_CUDA=true` می‌توان سرعت تولید را به شکل چشمگیری افزایش داد.
