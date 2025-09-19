"""Global pytest configuration for TTSKit tests."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ttskit.database.base import Base
from ttskit.database.models import APIKey, User


@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test."""
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
def test_db_with_data():
    """Create test database with sample data."""
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}
    )

    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        admin_user = User(
            user_id="admin",
            username="admin",
            email="admin@test.com",
            is_active=True,
            is_admin=True,
        )
        test_user = User(
            user_id="test_user",
            username="test_user",
            email="test@test.com",
            is_active=True,
            is_admin=False,
        )

        session.add(admin_user)
        session.add(test_user)
        session.commit()

        admin_key = APIKey(
            user_id="admin",
            api_key_hash="admin_hash_123",
            permissions='["read", "write", "admin"]',
            is_active=True,
            usage_count=0,
        )
        test_key = APIKey(
            user_id="test_user",
            api_key_hash="test_hash_456",
            permissions='["read", "write"]',
            is_active=True,
            usage_count=0,
        )

        session.add(admin_key)
        session.add(test_key)
        session.commit()

        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True, scope="function")
def mock_pyrogram_globally():
    """Mock pyrogram.Client globally for all tests to prevent network calls."""
    mock_client = AsyncMock()

    async def async_start():
        return None

    async def async_stop():
        return None

    async def async_send_message(*args, **kwargs):
        mock_message = Mock()
        mock_message.id = 123
        mock_message.chat.id = 456
        mock_message.from_user.id = 789
        mock_message.from_user.username = "testuser"
        mock_message.from_user.first_name = "Test"
        mock_message.from_user.last_name = "User"
        mock_message.from_user.language_code = "en"
        mock_message.from_user.is_bot = False
        mock_message.from_user.is_premium = False
        mock_message.text = kwargs.get("text", "Test message")
        mock_message.date = None
        mock_message.edit_date = None
        mock_message.media_group_id = None
        mock_message.caption = None
        mock_message.entities = None
        mock_message.voice = None
        mock_message.audio = None
        mock_message.document = None
        mock_message.photo = None
        mock_message.video = None
        mock_message.sticker = None
        mock_message.location = None
        mock_message.contact = None
        mock_message.poll = None
        mock_message.reply_to_message = None
        return mock_message

    async def async_send_voice(*args, **kwargs):
        return await async_send_message(*args, **kwargs)

    async def async_send_audio(*args, **kwargs):
        return await async_send_message(*args, **kwargs)

    async def async_send_document(*args, **kwargs):
        return await async_send_message(*args, **kwargs)

    async def async_edit_message_text(*args, **kwargs):
        return await async_send_message(*args, **kwargs)

    async def async_delete_messages(*args, **kwargs):
        return True

    async def async_get_chat(*args, **kwargs):
        mock_chat = Mock()
        mock_chat.id = 456
        mock_chat.type = "private"
        mock_chat.title = "Test Chat"
        mock_chat.username = "testchat"
        mock_chat.first_name = "Test"
        mock_chat.last_name = "Chat"
        mock_chat.description = "Test description"
        mock_chat.invite_link = "https://t.me/testchat"
        return mock_chat

    async def async_get_users(*args, **kwargs):
        mock_user = Mock()
        mock_user.id = 789
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.language_code = "en"
        mock_user.is_bot = False
        mock_user.is_premium = False
        return mock_user

    mock_client.start = async_start
    mock_client.stop = async_stop
    mock_client.send_message = async_send_message
    mock_client.send_voice = async_send_voice
    mock_client.send_audio = async_send_audio
    mock_client.send_document = async_send_document
    mock_client.edit_message_text = async_edit_message_text
    mock_client.delete_messages = async_delete_messages
    mock_client.get_chat = async_get_chat
    mock_client.get_users = async_get_users

    mock_client_class = MagicMock(return_value=mock_client)
    with (
        patch("pyrogram.Client", mock_client_class),
        patch("pyrogram.client.Client", mock_client_class),
        patch("ttskit.telegram.pyrogram_adapter.Client", mock_client_class),
        patch.dict(sys.modules, {"pyrogram": MagicMock(Client=mock_client_class)}),
    ):
        yield mock_client_class, mock_client


@pytest.fixture(autouse=True, scope="function")
def mock_telethon_globally():
    """Mock telethon.TelegramClient globally for all tests to prevent network calls."""
    mock_client = AsyncMock()

    async def async_start():
        return None

    async def async_disconnect():
        return None

    mock_start = Mock()
    mock_start.side_effect = async_start
    mock_disconnect = Mock()
    mock_disconnect.side_effect = async_disconnect
    mock_send_message = AsyncMock()
    mock_send_file = AsyncMock()
    default_mock_message = Mock()
    default_mock_message.id = 123
    default_mock_message.chat_id = 456
    default_mock_message.from_id = Mock()
    default_mock_message.from_id.id = 789
    default_mock_message.from_id.username = "testuser"
    default_mock_message.from_id.first_name = "Test"
    default_mock_message.from_id.last_name = "User"
    default_mock_message.from_id.lang_code = "en"
    default_mock_message.from_id.bot = False
    default_mock_message.from_id.premium = False
    default_mock_message.message = "Test message"
    default_mock_message.date = None
    default_mock_message.edit_date = None
    default_mock_message.grouped_id = None
    default_mock_message.entities = None
    default_mock_message.voice = None
    default_mock_message.audio = None
    default_mock_message.document = None
    default_mock_message.photo = None
    default_mock_message.video = None
    default_mock_message.sticker = None
    default_mock_message.geo = None
    default_mock_message.contact = None
    default_mock_message.poll = None
    default_mock_message.reply_to_msg_id = None

    mock_send_message.return_value = default_mock_message
    mock_send_file.return_value = default_mock_message

    mock_client.start = mock_start
    mock_client.disconnect = mock_disconnect
    mock_client.send_message = mock_send_message
    mock_client.send_file = mock_send_file

    mock_client_class = MagicMock(return_value=mock_client)

    with (
        patch("telethon.TelegramClient", mock_client_class),
        patch("ttskit.telegram.telethon_adapter.TelegramClient", mock_client_class),
    ):
        yield mock_client_class, mock_client


@pytest.fixture(autouse=True, scope="function")
def mock_aiogram_globally():
    """Mock aiogram.Bot globally for all tests to prevent network calls."""
    mock_bot = AsyncMock()

    async def async_send_message(*args, **kwargs):
        mock_message = Mock()
        mock_message.message_id = 123
        return mock_message

    mock_bot.send_message = async_send_message

    mock_bot_class = MagicMock(return_value=mock_bot)

    with (
        patch("aiogram.Bot", mock_bot_class),
        patch("ttskit.telegram.aiogram_adapter.Bot", mock_bot_class),
    ):
        yield mock_bot_class, mock_bot


@pytest.fixture(autouse=True, scope="function")
def mock_telebot_globally():
    """Mock telebot.TeleBot globally for all tests to prevent network calls."""
    mock_bot = AsyncMock()

    async def async_send_message(*args, **kwargs):
        mock_message = Mock()
        mock_message.message_id = 123
        return mock_message

    async def async_stop_polling():
        return None

    mock_bot.send_message = async_send_message
    mock_bot.stop_polling = async_stop_polling

    mock_bot_class = MagicMock(return_value=mock_bot)

    with (
        patch("telebot.TeleBot", mock_bot_class),
        patch("ttskit.telegram.telebot_adapter.TeleBot", mock_bot_class),
    ):
        yield mock_bot_class, mock_bot


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "real_engine: marks tests that use real engines")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip slow tests in fast mode."""
    if config.getoption("--fast"):
        skip_slow = pytest.mark.skip(reason="Skipped in fast mode")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--fast",
        action="store_true",
        default=False,
        help="Run only fast tests (skip slow tests)",
    )
    parser.addoption(
        "--real-engines",
        action="store_true",
        default=False,
        help="Run real engine tests (slower but more comprehensive)",
    )


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return {
        "fast_mode": os.getenv("TTSKIT_TEST_FAST", "false").lower() == "true",
        "real_engines": os.getenv("TTSKIT_TEST_REAL_ENGINES", "false").lower()
        == "true",
        "skip_slow": os.getenv("TTSKIT_SKIP_SLOW", "false").lower() == "true",
    }


@pytest.fixture
def mock_engine():
    """Mock engine for testing."""
    engine = Mock()
    engine.is_available.return_value = True
    engine.synth_async.return_value = b"fake_audio_data"
    engine.list_voices.return_value = ["voice1", "voice2"]
    engine.get_capabilities.return_value = Mock(
        offline=False,
        ssml=False,
        rate_control=False,
        pitch_control=False,
        languages=["en", "fa"],
        voices=["voice1", "voice2"],
        max_text_length=5000,
    )
    return engine


@pytest.fixture
def mock_tts():
    """Mock TTS instance for testing."""
    tts = Mock()
    tts.synth_async.return_value = Mock(
        data=b"fake_audio_data", format="ogg", duration=1.0, size=1024, engine="gtts"
    )
    tts.list_voices.return_value = ["voice1", "voice2"]
    tts.get_stats.return_value = {
        "total_requests": 10,
        "successful_requests": 8,
        "failed_requests": 2,
    }
    return tts


@pytest.fixture(autouse=True, scope="function")
def mock_redis_globally():
    """Mock Redis globally for all tests to prevent external connections."""
    mock_redis = AsyncMock()

    async def async_ping():
        return True

    async def async_get(key):
        return None

    async def async_set(key, value, ex=None):
        return True

    async def async_setex(key, time, value):
        return True

    async def async_expire(key, time):
        return True

    async def async_delete(key):
        return 1

    async def async_exists(key):
        return False

    async def async_incr(key):
        return 1

    async def async_incrby(key, amount):
        return amount

    async def async_hget(key, field):
        return None

    async def async_hset(key, field, value):
        return 1

    async def async_hgetall(key):
        return {}

    async def async_hdel(key, field):
        return 1

    async def async_lpush(key, value):
        return 1

    async def async_rpop(key):
        return None

    async def async_llen(key):
        return 0

    async def async_pipeline():
        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = []
        return mock_pipeline

    mock_redis.ping = async_ping
    mock_redis.get = async_get
    mock_redis.set = async_set
    mock_redis.setex = async_setex
    mock_redis.expire = async_expire
    mock_redis.delete = async_delete
    mock_redis.exists = async_exists
    mock_redis.incr = async_incr
    mock_redis.incrby = async_incrby
    mock_redis.hget = async_hget
    mock_redis.hset = async_hset
    mock_redis.hgetall = async_hgetall
    mock_redis.hdel = async_hdel
    mock_redis.lpush = async_lpush
    mock_redis.rpop = async_rpop
    mock_redis.llen = async_llen
    mock_redis.pipeline = async_pipeline

    mock_redis_class = MagicMock(return_value=mock_redis)

    with (
        patch("redis.asyncio.Redis", mock_redis_class),
        patch("redis.Redis", mock_redis_class),
        patch("ttskit.cache.redis.redis", MagicMock()),
        patch("ttskit.utils.rate_limiter.redis", MagicMock()),
    ):
        yield mock_redis_class, mock_redis


@pytest.fixture(autouse=True, scope="function")
def mock_httpx_globally():
    """Mock httpx globally for all tests to prevent HTTP requests."""
    mock_client = AsyncMock()

    async def async_get(url, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Mock response"
        mock_response.json.return_value = {"status": "success"}
        mock_response.content = b"Mock content"
        mock_response.headers = {"content-type": "application/json"}
        return mock_response

    async def async_post(url, **kwargs):
        return await async_get(url, **kwargs)

    async def async_put(url, **kwargs):
        return await async_get(url, **kwargs)

    async def async_delete(url, **kwargs):
        return await async_get(url, **kwargs)

    mock_client.get = async_get
    mock_client.post = async_post
    mock_client.put = async_put
    mock_client.delete = async_delete

    mock_client_class = MagicMock(return_value=mock_client)

    with (
        patch("httpx.AsyncClient", mock_client_class),
        patch("httpx.Client", mock_client_class),
        patch(
            "ttskit.utils.performance.httpx", MagicMock(AsyncClient=mock_client_class)
        ),
    ):
        yield mock_client_class, mock_client


@pytest.fixture(autouse=True, scope="function")
def mock_aiofiles_globally():
    """Mock aiofiles globally for all tests to prevent file I/O."""

    async def async_open(filepath, mode="r", **kwargs):
        mock_file = AsyncMock()
        mock_file.read.return_value = b"Mock file content"
        mock_file.write.return_value = None
        mock_file.close.return_value = None
        mock_file.__aenter__.return_value = mock_file
        mock_file.__aexit__.return_value = None
        return mock_file

    mock_aiofiles = MagicMock()
    mock_aiofiles.open = async_open

    with (
        patch("aiofiles.open", async_open),
        patch("ttskit.utils.performance.aiofiles", mock_aiofiles),
        patch("ttskit.metrics.advanced.aiofiles", mock_aiofiles),
    ):
        yield mock_aiofiles


@pytest.fixture(autouse=True, scope="function")
def mock_audio_libraries_globally():
    """Mock audio libraries globally for all tests."""
    import numpy as np

    mock_librosa = MagicMock()
    mock_librosa.resample.return_value = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    mock_librosa.effects.trim.return_value = (
        np.array([0.1, 0.2, 0.1], dtype=np.float32),
        0,
    )
    mock_librosa.load.return_value = (
        np.array([0.1, 0.2, 0.1], dtype=np.float32),
        22050,
    )

    mock_soundfile = MagicMock()
    mock_soundfile.read.return_value = (
        np.array([0.1, 0.2, 0.1], dtype=np.float32),
        22050,
    )

    def mock_write(filepath, data, samplerate):
        with open(filepath, "wb") as f:
            f.write(b"fake_audio_data")

    mock_soundfile.write.side_effect = mock_write

    mock_pydub = MagicMock()
    mock_audio_segment = MagicMock()
    mock_audio_segment.from_file.return_value = mock_audio_segment
    mock_audio_segment.__add__.return_value = mock_audio_segment
    mock_audio_segment.__iadd__.return_value = mock_audio_segment
    mock_audio_segment.frame_rate = 22050
    mock_audio_segment.channels = 1
    mock_audio_segment.sample_width = 2
    mock_audio_segment.duration_seconds = 0.1

    mock_export_result = MagicMock()
    mock_export_result.read.return_value = b"fake_merged_audio_data" * 1000
    mock_export_result.__enter__.return_value = mock_export_result
    mock_export_result.__exit__.return_value = None
    mock_audio_segment.export.return_value = mock_export_result

    mock_pydub.AudioSegment = MagicMock(return_value=mock_audio_segment)

    with (
        patch("ttskit.audio.pipeline.librosa", mock_librosa),
        patch("ttskit.audio.pipeline.soundfile", mock_soundfile),
        patch("ttskit.audio.pipeline.AudioSegment", mock_audio_segment),
        patch("ttskit.audio.pipeline.SCIPY_AVAILABLE", False),
        patch("ttskit.audio.pipeline._scipy_signal", MagicMock()),
    ):
        yield {
            "librosa": mock_librosa,
            "soundfile": mock_soundfile,
            "pydub": mock_pydub,
        }


@pytest.fixture(autouse=True, scope="function")
def mock_onnx_globally():
    """Mock ONNX and ONNXRuntime globally for all tests."""
    mock_onnx = MagicMock()
    mock_onnx.load_model.return_value = MagicMock()

    mock_ort = MagicMock()
    mock_session = MagicMock()
    mock_session.run.return_value = [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
    mock_ort.InferenceSession.return_value = mock_session

    with (
        patch("ttskit.engines.piper_engine.PiperVoice", MagicMock()),
        patch("ttskit.engines.piper_engine.SynthesisConfig", MagicMock()),
    ):
        yield {
            "onnx": mock_onnx,
            "onnxruntime": mock_ort,
        }


@pytest.fixture(autouse=True, scope="function")
def mock_tts_library_globally():
    """Mock TTS library globally for all tests."""
    mock_tts = MagicMock()
    mock_tts.tts.return_value = b"fake_tts_audio_data"
    mock_tts.list_models.return_value = ["model1", "model2"]

    with (
        patch("ttskit.engines.gtts_engine.gTTS", MagicMock()),
    ):
        yield mock_tts


@pytest.fixture(autouse=True, scope="function")
def mock_psutil_globally():
    """Mock psutil globally for all tests."""
    mock_psutil = MagicMock()
    mock_psutil.cpu_percent.return_value = 25.5
    mock_psutil.virtual_memory.return_value = MagicMock(
        total=8589934592,  # 8GB
        available=4294967296,  # 4GB
        percent=50.0,
        used=4294967296,
        free=4294967296,
    )
    mock_psutil.disk_usage.return_value = MagicMock(
        total=1000000000000,  # 1TB
        used=500000000000,  # 500GB
        free=500000000000,  # 500GB
        percent=50.0,
    )

    with (
        patch("ttskit.health.psutil", mock_psutil),
        patch("ttskit.metrics.advanced.psutil", mock_psutil),
    ):
        yield mock_psutil


@pytest.fixture(autouse=True, scope="function")
def mock_prometheus_globally():
    """Mock prometheus-client globally for all tests."""
    mock_prometheus = MagicMock()
    mock_counter = MagicMock()
    mock_counter.inc.return_value = None
    mock_gauge = MagicMock()
    mock_gauge.set.return_value = None
    mock_histogram = MagicMock()
    mock_histogram.observe.return_value = None

    mock_prometheus.Counter.return_value = mock_counter
    mock_prometheus.Gauge.return_value = mock_gauge
    mock_prometheus.Histogram.return_value = mock_histogram

    with (
        patch("ttskit.metrics.advanced.aiofiles", MagicMock()),
        patch("ttskit.metrics.advanced.psutil", MagicMock()),
    ):
        yield mock_prometheus


@pytest.fixture(autouse=True, scope="function")
def mock_file_operations_globally():
    """Mock file operations globally for all tests."""
    mock_tempfile = MagicMock()
    mock_tempfile.mkstemp.return_value = (1, "/tmp/test_file")
    mock_tempfile.mkdtemp.return_value = "/tmp/test_dir"
    mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value = MagicMock()

    mock_shutil = MagicMock()
    mock_shutil.rmtree.return_value = None
    mock_shutil.copy2.return_value = None
    mock_shutil.move.return_value = None

    mock_pathlib = MagicMock()
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.is_file.return_value = True
    mock_path.is_dir.return_value = False
    mock_path.mkdir.return_value = None
    mock_path.unlink.return_value = None
    mock_pathlib.Path.return_value = mock_path

    with (
        patch("ttskit.utils.temp_manager.tempfile", mock_tempfile),
        patch("ttskit.utils.temp_manager.shutil", mock_shutil),
        patch("ttskit.utils.temp_manager.Path", mock_pathlib.Path),
    ):
        yield {
            "tempfile": mock_tempfile,
            "shutil": mock_shutil,
            "pathlib": mock_pathlib,
        }


@pytest.fixture(autouse=True, scope="function")
def mock_subprocess_globally():
    """Mock subprocess operations globally for all tests."""
    mock_subprocess = MagicMock()
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = b"Mock output"
    mock_process.stderr = b""
    mock_process.communicate.return_value = (b"Mock output", b"")
    mock_subprocess.run.return_value = mock_process
    mock_subprocess.Popen.return_value = mock_process

    with (
        patch("ttskit.utils.performance.asyncio", MagicMock()),
    ):
        yield mock_subprocess


@pytest.fixture(autouse=True, scope="function")
def mock_time_globally():
    """Mock time operations globally for all tests."""
    mock_time = MagicMock()
    mock_time.time.return_value = 1640995200.0  # Fixed timestamp
    mock_time.sleep.return_value = None

    with (
        patch("ttskit.metrics.advanced.datetime", MagicMock()),
    ):
        yield mock_time


@pytest.fixture(autouse=True, scope="function")
def mock_json_globally():
    """Mock JSON operations globally for all tests."""
    mock_json = MagicMock()
    mock_json.dumps.return_value = '{"status": "success"}'
    mock_json.loads.return_value = {"status": "success"}

    with (
        patch("ttskit.utils.performance.httpx", MagicMock()),
        patch("ttskit.utils.performance.aiofiles", MagicMock()),
    ):
        yield mock_json


@pytest.fixture(autouse=True, scope="function")
def mock_hashlib_globally():
    """Mock hashlib operations globally for all tests."""
    mock_hashlib = MagicMock()
    mock_hash = MagicMock()
    mock_hash.hexdigest.return_value = "mock_hash_value"
    mock_hashlib.sha256.return_value = mock_hash
    mock_hashlib.md5.return_value = mock_hash

    yield mock_hashlib


@pytest.fixture(autouse=True, scope="function")
def mock_secrets_globally():
    """Mock secrets operations globally for all tests."""
    mock_secrets = MagicMock()
    mock_secrets.token_urlsafe.return_value = "mock_secret_token"
    mock_secrets.token_hex.return_value = "mock_hex_token"

    yield mock_secrets


@pytest.fixture(autouse=True, scope="function")
def mock_logging_globally():
    """Mock logging operations globally for all tests."""
    mock_logger = MagicMock()
    mock_logger.info.return_value = None
    mock_logger.warning.return_value = None
    mock_logger.error.return_value = None
    mock_logger.debug.return_value = None
    mock_logger.critical.return_value = None

    mock_logging_module = MagicMock()
    mock_logging_module.getLogger.return_value = mock_logger

    with (
        patch("ttskit.utils.logging_config.logging", mock_logging_module),
    ):
        yield mock_logging_module


@pytest.fixture(autouse=True, scope="function")
def mock_config_globally():
    """Mock configuration operations globally for all tests."""
    mock_config = MagicMock()
    mock_config.settings = MagicMock()
    mock_config.settings.database_url = "sqlite:///:memory:"
    mock_config.settings.redis_url = "redis://localhost:6379"
    mock_config.settings.bot_token = "mock_bot_token"
    mock_config.settings.api_key = "mock_api_key"
    mock_config.settings.debug = True
    mock_config.settings.test_mode = True

    with (
        patch("ttskit.config", mock_config),
        patch("ttskit.api.dependencies.settings", mock_config.settings),
    ):
        yield mock_config


@pytest.fixture(autouse=True, scope="function")
def mock_asyncio_globally():
    """Mock asyncio operations globally for all tests."""
    mock_asyncio = MagicMock()
    mock_asyncio.sleep.return_value = None
    mock_asyncio.gather.return_value = []
    mock_asyncio.create_task.return_value = MagicMock()

    with (
        patch("ttskit.utils.performance.asyncio", mock_asyncio),
    ):
        yield mock_asyncio


@pytest.fixture(autouse=True, scope="function")
def mock_threading_globally():
    """Mock threading operations globally for all tests."""
    mock_threading = MagicMock()
    mock_thread = MagicMock()
    mock_thread.start.return_value = None
    mock_thread.join.return_value = None
    mock_threading.Thread.return_value = mock_thread

    with (
        patch("ttskit.utils.performance.Path", MagicMock()),
    ):
        yield mock_threading


@pytest.fixture(autouse=True, scope="function")
def mock_multiprocessing_globally():
    """Mock multiprocessing operations globally for all tests."""
    mock_multiprocessing = MagicMock()
    mock_process = MagicMock()
    mock_process.start.return_value = None
    mock_process.join.return_value = None
    mock_process.terminate.return_value = None
    mock_multiprocessing.Process.return_value = mock_process

    with (
        patch("ttskit.utils.performance.asyncio", MagicMock()),
    ):
        yield mock_multiprocessing


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    os.environ["TTSKIT_TEST_MODE"] = "true"
    os.environ["TTSKIT_CACHE_ENABLED"] = "false"

    yield

    if "TTSKIT_TEST_MODE" in os.environ:
        del os.environ["TTSKIT_TEST_MODE"]
    if "TTSKIT_CACHE_ENABLED" in os.environ:
        del os.environ["TTSKIT_CACHE_ENABLED"]


# Skip real engine tests by default unless explicitly requested
def pytest_runtest_setup(item):
    """Skip real engine tests unless explicitly requested."""
    if "real_engine" in item.keywords:
        if not item.config.getoption("--real-engines"):
            pytest.skip("Real engine tests skipped (use --real-engines to run)")


# Performance test markers
@pytest.fixture
def performance_config():
    """Performance test configuration."""
    return {
        "max_duration": 5.0,  # Max test duration in seconds
        "max_memory_mb": 100,  # Max memory usage in MB
        "timeout": 30,  # Test timeout in seconds
    }
