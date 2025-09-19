"""Extra coverage tests for AudioManager without modifying source file."""

import io
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ttskit.utils.audio_manager import (
    AudioManager,
    audio_manager,
)
from ttskit.utils.audio_manager import (
    clear_cache as global_clear_cache,
)
from ttskit.utils.audio_manager import (
    get_audio as global_get_audio,
)
from ttskit.utils.audio_manager import (
    get_cache_stats as global_get_cache_stats,
)


@pytest.fixture()
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _make_manager(tmp: Path, max_size: int = 1000, max_age: int = 3600) -> AudioManager:
    return AudioManager(
        cache_dir=str(tmp), max_cache_size=max_size, max_file_age=max_age
    )


def test_save_to_cache_compat_and_get_file_info_and_list(temp_dir: Path):
    m = _make_manager(temp_dir)
    key = "k1"
    data = b"d1"
    m._save_to_cache_compat(key, data)

    info = m.get_file_info(key)
    assert info is not None
    assert info["file_exists"] is True
    assert info["size"] == len(data)
    assert Path(info["file_path"]).exists()

    listed = m.list_cached_files()
    assert isinstance(listed, list) and listed
    assert any(i and i.get("file_exists") for i in listed)


def test_remove_file_with_mp3_format_path(temp_dir: Path):
    m = _make_manager(temp_dir)
    key = "k_mp3"
    (temp_dir / f"{key}.mp3").write_bytes(b"x")
    m.cache_index[key] = {
        "format": "mp3",
        "size": 1,
        "created": time.time(),
        "last_accessed": time.time(),
        "metadata": {"format": "mp3"},
    }
    assert m.remove_file(key) is True
    assert key not in m.cache_index
    assert not (temp_dir / f"{key}.mp3").exists()


def test_export_cache_generates_named_files(temp_dir: Path):
    m = _make_manager(temp_dir)
    key = "exp1"
    (temp_dir / f"{key}.mp3").write_bytes(b"mp3data")
    m.cache_index[key] = {
        "format": "mp3",
        "size": 7,
        "created": time.time(),
        "last_accessed": time.time(),
        "metadata": {"engine": "gtts", "lang": "en"},
    }
    out = temp_dir / "out"
    m.export_cache(str(out))
    files = list(out.glob("*.mp3"))
    assert files and files[0].name.endswith(".mp3")
    assert "gtts_en_" in files[0].name or files[0].stat().st_size == 7


@pytest.mark.asyncio
async def test_module_level_get_audio_calls_global_instance(temp_dir: Path):
    with patch.object(audio_manager, "get_audio", return_value=b"ok") as pg:
        res = await global_get_audio("t", "en", "gtts")
        assert res == b"ok"
        pg.assert_called_once()


def test_module_level_clear_cache_and_get_cache_stats(temp_dir: Path):
    m = _make_manager(temp_dir)
    m._save_to_cache("a", b"1")
    assert (temp_dir / "a.ogg").exists()
    orig_dir = audio_manager.cache_dir
    try:
        audio_manager.cache_dir = m.cache_dir
        global_clear_cache()
        assert not (temp_dir / "a.ogg").exists()
        stats = global_get_cache_stats()
        assert isinstance(stats, dict) and "hit_rate" in stats
    finally:
        audio_manager.cache_dir = orig_dir


def test_cleanup_cache_removes_oldest_when_exceeding_max_size(temp_dir: Path):
    m = _make_manager(temp_dir, max_size=2)
    for idx in range(3):
        key = f"k{idx}"
        m._save_to_cache(key, f"d{idx}".encode())
        m.cache_index[key]["last_accessed"] = idx
        p = temp_dir / f"{key}.ogg"
        os.utime(p, (time.time(), time.time()))
    m._cleanup_cache()
    assert (temp_dir / "k0.ogg").exists() is False
    assert len(m.cache_index) == 2


def test_cleanup_old_files_removes_based_on_age_and_index(temp_dir: Path):
    m = _make_manager(temp_dir, max_age=1)
    oldf = temp_dir / "old.ogg"
    newf = temp_dir / "new.ogg"
    oldf.write_bytes(b"o")
    newf.write_bytes(b"n")
    very_old = time.time() - 10_000
    os.utime(oldf, (very_old, very_old))
    m.cache_index["old"] = {
        "format": "ogg",
        "metadata": {},
        "created": very_old,
        "last_accessed": very_old,
    }
    m.cache_index["new"] = {
        "format": "ogg",
        "metadata": {},
        "created": time.time(),
        "last_accessed": time.time(),
    }
    m.cleanup_old_files()
    assert not oldf.exists()
    assert newf.exists()
    assert "old" not in m.cache_index
    assert "new" in m.cache_index


@pytest.mark.asyncio
async def test_process_audio_noop_and_pipeline_and_fallback(temp_dir: Path):
    m = _make_manager(temp_dir)
    out = await AudioManager.process_audio(
        m, b"abc", input_format="mp3", output_format="mp3"
    )
    assert out == b"abc"

    fake_bytes = b"converted"
    with patch(
        "ttskit.audio.pipeline.pipeline.convert_format", return_value=fake_bytes
    ):
        out2 = await AudioManager.process_audio(
            m, b"xyz", input_format="mp3", output_format="ogg"
        )
        assert out2 == fake_bytes

    class _FakeSeg:
        def __init__(self):
            self.frame_rate = 22050
            self.channels = 1
            self.sample_width = 2

        @classmethod
        def from_file(cls, fobj, format):
            return cls()

        def export(self, buf, format):
            if isinstance(buf, io.BytesIO):
                buf.write(b"fallback")
                return buf
            raise RuntimeError("expected BytesIO")

    with (
        patch(
            "ttskit.audio.pipeline.pipeline.convert_format",
            side_effect=Exception("boom"),
        ),
        patch.dict("sys.modules", {"pydub": MagicMock(AudioSegment=_FakeSeg)}),
    ):
        out3 = await AudioManager.process_audio(
            m, b"raw", input_format="mp3", output_format="ogg"
        )
        assert out3 in (b"fallback", b"raw")


def test_public_save_to_cache_wrapper_success_and_error(temp_dir: Path):
    m = _make_manager(temp_dir)
    m.save_to_cache("s", b"1", format="ogg")
    assert (temp_dir / "s.ogg").exists()
    with patch.object(m, "_save_to_cache", side_effect=Exception("err")):
        m.save_to_cache("x", b"2", format="ogg")
        assert not (temp_dir / "x.ogg").exists()


def test_load_cache_index_error_and_save_cache_index_error(temp_dir: Path, monkeypatch):
    m = _make_manager(temp_dir)
    idx = temp_dir / "cache_index.json"
    idx.write_text("{invalid_json}")
    m._load_cache_index()

    def _bad_open(*args, **kwargs):
        raise OSError("disk full")

    with patch("builtins.open", _bad_open):
        m._save_cache_index()


def test_is_cache_valid_missing_file_and_too_old(temp_dir: Path):
    m = _make_manager(temp_dir, max_age=1)
    m.cache_index["absent"] = {"format": "ogg"}
    assert m._is_cache_valid("absent") is False
    key = "oldage"
    (temp_dir / f"{key}.ogg").write_bytes(b"x")
    m.cache_index[key] = {"format": "ogg"}
    very_old = time.time() - 10_000
    os.utime(temp_dir / f"{key}.ogg", (very_old, very_old))
    assert m._is_cache_valid(key) is False


def test_is_cached_true_via_index_valid(temp_dir: Path):
    m = _make_manager(temp_dir)
    key = "ix"
    m._save_to_cache(key, b"d")
    assert m._is_cached(key) is True


@pytest.mark.asyncio
async def test_get_audio_compat_save_on_typeerror(temp_dir: Path):
    m = _make_manager(temp_dir)
    with patch("ttskit.utils.audio_manager.global_cache_key", return_value="kTT"):
        with patch.object(m, "_generate_audio", return_value=b"z"):
            with patch.object(m, "_save_to_cache", side_effect=TypeError("sig")):

                def _fake_compat(cache_key, audio_data):
                    p = temp_dir / f"{cache_key}.ogg"
                    p.write_bytes(audio_data)
                    m.cache_index[cache_key] = {
                        "format": "ogg",
                        "size": len(audio_data),
                        "created": time.time(),
                        "last_accessed": time.time(),
                        "metadata": {"format": "ogg"},
                    }

                with patch.object(m, "_save_to_cache_compat", side_effect=_fake_compat):
                    out = await m.get_audio("t", "en", "gtts", format="wav")
                    assert out == b"z"
                    assert (temp_dir / "kTT.ogg").exists()


@pytest.mark.asyncio
async def test_generate_audio_awaitable_engine_result(temp_dir: Path):
    m = _make_manager(temp_dir)

    class _Async:
        def __await__(self):
            async def _coro():
                return b"A"

            return _coro().__await__()

    fake_engine = MagicMock()
    fake_engine.synth_async.return_value = _Async()
    with patch("ttskit.utils.audio_manager.engine_registry") as reg:
        reg.engines = {"gtts": fake_engine}
        out = await m._generate_audio("t", "en", "gtts", None, None, "mp3")
        assert out == b"A"


@pytest.mark.asyncio
async def test_generate_audio_smart_router_tuple_and_audio_data_shortcut(
    temp_dir: Path,
):
    m = _make_manager(temp_dir)

    class _Router:
        async def synth_async(self, **kwargs):
            return (b"audio_data", "some")

    with patch("ttskit.utils.audio_manager.SmartRouter", return_value=_Router()):
        out = await m._generate_audio(
            "t", "en", engine="", voice=None, effects=None, format="wav"
        )
        assert out == b"audio_data"


@pytest.mark.asyncio
async def test_generate_audio_piper_wav_skips_processing(temp_dir: Path):
    m = _make_manager(temp_dir)
    fake_engine = MagicMock()
    fake_engine.synth_async.return_value = b"W"
    with patch("ttskit.utils.audio_manager.engine_registry") as reg:
        reg.engines = {"piper": fake_engine}
        out = await m._generate_audio("t", "fa", "piper", None, None, "wav")
        assert out == b"W"


def test_get_from_cache_exception_handling(temp_dir: Path):
    m = _make_manager(temp_dir)
    m.cache_index["e"] = {"format": "ogg"}
    (temp_dir / "e.ogg").write_bytes(b"x")
    with patch.object(m, "_load_from_cache", side_effect=RuntimeError("x")):
        assert m.get_from_cache("e") is None


def test_clear_cache_unlink_exception_is_ignored(temp_dir: Path, monkeypatch):
    m = _make_manager(temp_dir)
    p = temp_dir / "a.ogg"
    p.write_bytes(b"x")
    orig_unlink = Path.unlink

    def bad_unlink(self):
        if str(self).endswith("a.ogg"):
            raise OSError("busy")
        return orig_unlink(self)

    monkeypatch.setattr(Path, "unlink", bad_unlink)
    m.clear_cache()
    assert True


def test_cleanup_old_files_exception_paths(temp_dir: Path, monkeypatch):
    m = _make_manager(temp_dir, max_age=1)
    f1 = temp_dir / "x1.ogg"
    f2 = temp_dir / "x2.ogg"
    f1.write_bytes(b"1")
    f2.write_bytes(b"2")
    orig_stat = Path.stat

    def bad_stat_disk(self, *args, **kwargs):
        if str(self).endswith("x1.ogg"):
            raise OSError("nope")
        return orig_stat(self)

    monkeypatch.setattr(Path, "stat", bad_stat_disk)
    m.cleanup_old_files()

    m.cache_index["x1"] = {"format": "ogg"}
    m.cache_index["x2"] = {"format": "ogg"}

    orig_exists = Path.exists

    def exists_override(self):
        if str(self).endswith("x2.ogg"):
            return True
        return orig_exists(self)

    monkeypatch.setattr(Path, "exists", exists_override)

    def bad_stat_index(self, *args, **kwargs):
        if str(self).endswith("x2.ogg"):
            raise OSError("bad")
        return orig_stat(self)

    monkeypatch.setattr(Path, "stat", bad_stat_index)
    m.cleanup_old_files()
    assert True


def test_get_file_info_none_and_helper_methods(temp_dir: Path):
    m = _make_manager(temp_dir)
    assert m.get_file_info("missing") is None
    info = AudioManager.get_audio_info(m, b"12345")
    assert info["size"] == 5 and info["sample_rate"] == 48000


@pytest.mark.asyncio
async def test_generate_audio_processing_awaits_pipeline_conversion(temp_dir: Path):
    m = _make_manager(temp_dir)
    fake_engine = MagicMock()
    fake_engine.synth_async.return_value = b"BZ"
    with (
        patch("ttskit.utils.audio_manager.engine_registry") as reg,
        patch("ttskit.audio.pipeline.pipeline.convert_format", return_value=b"PROC"),
    ):
        reg.engines = {"gtts": fake_engine}
        out = await m._generate_audio("t", "en", "gtts", None, None, "wav")
        assert out == b"PROC"


def test_remove_file_returns_false_when_missing(temp_dir: Path):
    m = _make_manager(temp_dir)
    assert m.remove_file("nope") is False


def test_cleanup_old_files_unlink_exception_in_index_loop(temp_dir: Path, monkeypatch):
    m = _make_manager(temp_dir, max_age=1)
    key = "oldunlink"
    p = temp_dir / f"{key}.ogg"
    p.write_bytes(b"x")
    old = time.time() - 10_000
    os.utime(p, (old, old))
    m.cache_index[key] = {"format": "ogg"}
    orig_unlink = Path.unlink

    def bad_unlink(self):
        if str(self).endswith(f"{key}.ogg"):
            raise OSError("deny")
        return orig_unlink(self)

    monkeypatch.setattr(Path, "unlink", bad_unlink)
    m.cleanup_old_files()
    assert key not in m.cache_index


@pytest.mark.asyncio
async def test_generate_audio_piper_to_ogg_sets_input_wav(temp_dir: Path):
    m = _make_manager(temp_dir)
    fake_engine = MagicMock()
    fake_engine.synth_async.return_value = b"W"
    captured = {"args": None}

    def conv(data, input_format, output_format):
        captured["args"] = (input_format, output_format)
        return b"OK"

    with (
        patch("ttskit.utils.audio_manager.engine_registry") as reg,
        patch("ttskit.audio.pipeline.pipeline.convert_format", side_effect=conv),
    ):
        reg.engines = {"piper": fake_engine}
        out = await m._generate_audio("t", "fa", "piper", None, None, "ogg")
        assert out == b"OK"
        assert captured["args"] == ("wav", "ogg")


def test_cleanup_old_files_stale_index_triggers_save(temp_dir: Path):
    m = _make_manager(temp_dir)
    m.cache_index["stale_key"] = {"format": "ogg"}
    called = {"v": 0}

    def _save_index():
        called["v"] += 1

    with patch.object(m, "_save_cache_index", side_effect=_save_index):
        m.cleanup_old_files()
        assert called["v"] >= 1


@pytest.mark.asyncio
async def test_process_audio_double_fallback_returns_input_for_ogg(temp_dir: Path):
    m = _make_manager(temp_dir)
    with (
        patch(
            "ttskit.audio.pipeline.pipeline.convert_format",
            side_effect=Exception("boom"),
        ),
        patch.dict("sys.modules", {"pydub": MagicMock(AudioSegment=MagicMock())}),
    ):
        import sys

        sys.modules["pydub"].AudioSegment.from_file.side_effect = Exception(
            "pydub_fail"
        )
        data = b"IN"
        out = await AudioManager.process_audio(
            m, data, input_format="mp3", output_format="ogg"
        )
        assert out == data
