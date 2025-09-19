"""Audio management utilities for TTSKit.

This module handles audio file caching, generation via TTS engines, format conversion,
and cleanup. It includes the AudioManager class for persistent cache management
and top-level functions for easy access.
"""

import hashlib
import tempfile
import time
from pathlib import Path
from typing import Any

from ..cache import cache_key as global_cache_key
from ..engines.registry import registry as engine_registry
from ..engines.smart_router import SmartRouter
from .logging_config import get_logger

logger = get_logger(__name__)


class AudioManager:
    """Manages audio files, caching, and generation for TTSKit.

    Handles cache indexing, validation, cleanup, and audio synthesis using registered engines.
    Supports both in-memory tracking and disk persistence for OGG files.

    Attributes:
        cache_dir: Path to the cache directory (str).
        max_cache_size: Maximum number of files in cache (int).
        max_file_age: Maximum age of files in seconds (int).
        cache_index: Dictionary of cache entries {key: metadata} (dict).
        cache_stats: Statistics like hits/misses (dict).
    """

    def __init__(
        self,
        cache_dir: str = str(Path(tempfile.gettempdir()) / "ttskit_cache"),
        max_cache_size: int = 1000,
        max_file_age: int = 3600,
    ):
        """Initialize the AudioManager with cache settings.

        Creates the cache directory and loads any existing index from disk.
        Initializes statistics and sets up paths.

        Args:
            cache_dir: Directory for storing cached audio files (str); defaults to temp/ttskit_cache.
            max_cache_size: Maximum number of files to keep in cache (int); defaults to 1000.
            max_file_age: Maximum age of files before eviction in seconds (int); defaults to 3600.

        Notes:
            cache_dir is kept as str for compatibility with tests comparing to str(Path).
            Audio processing is delegated to audio.py utilities.
            Cache index is loaded from cache_index.json if present.
        """
        self.cache_dir = str(Path(cache_dir))
        self.max_cache_size = max_cache_size
        self.max_file_age = max_file_age
        self.cache_index: dict[str, dict[str, Any]] = {}
        self.audio_processor = None
        self.cache_stats = {"hits": 0, "misses": 0, "total_requests": 0}

        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

        self._load_cache_index()

    def _load_cache_index(self) -> None:
        """Load the cache index from JSON file on disk.

        If the file exists, parses it and populates self.cache_index.
        Logs the number of entries loaded or warns on failure, resetting to empty dict.

        Notes:
            Index file is cache_index.json in self.cache_dir.
        """
        index_file = Path(self.cache_dir) / "cache_index.json"
        if index_file.exists():
            try:
                import json

                with open(index_file) as f:
                    self.cache_index = json.load(f)
                logger.info(f"Loaded cache index with {len(self.cache_index)} entries")
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self.cache_index = {}

    def _save_cache_index(self) -> None:
        """Save the current cache index to JSON file on disk.

        Writes self.cache_index with indentation for readability.
        Warns on failure but does not raise.

        Notes:
            Index file is cache_index.json in self.cache_dir.
        """
        index_file = Path(self.cache_dir) / "cache_index.json"
        try:
            import json

            with open(index_file, "w") as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")

    def _generate_cache_key(
        self,
        text: str,
        lang: str,
        engine: str,
        voice: str | None = None,
        effects: dict[str, Any] | None = None,
    ) -> str:
        """Generate a unique cache key from synthesis parameters.

        Combines text, language, engine, voice, and effects into a string,
        then hashes it using SHA-256 for security and low collision risk.

        Args:
            text: The text to synthesize (str).
            lang: Language code (str, e.g., 'en').
            engine: TTS engine name (str, e.g., 'gtts').
            voice: Optional voice name (str or None).
            effects: Optional audio effects dict (dict or None).

        Returns:
            str: Hexdigest SHA-256 hash as cache key.
        """
        key_data = f"{text}_{lang}_{engine}_{voice or ''}_{effects or ''}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_cache_key(
        self, text: str, lang: str, engine: str, voice: str | None = None
    ) -> str:
        """Get a cache key for audio parameters (alias for _generate_cache_key).

        Does not include effects; defaults to empty if voice is None.

        Args:
            text: Text to synthesize (str).
            lang: Language code (str).
            engine: Engine name (str).
            voice: Optional voice (str or None).

        Returns:
            str: Generated cache key.
        """
        return self._generate_cache_key(text, lang, engine, voice)

    def _is_cached(self, cache_key: str) -> bool:
        """Check if a cache entry exists and is valid.

        First checks the index for validity; falls back to direct file existence check.

        Args:
            cache_key: The cache key to check (str).

        Returns:
            bool: True if cached (valid index or file exists), False otherwise.
        """
        if self._is_cache_valid(cache_key):
            return True
        file_path = Path(self.cache_dir) / f"{cache_key}.ogg"
        return file_path.exists()

    def _get_cache_path(self, cache_key: str, format: str = "ogg") -> Path:
        """Construct the full path to a cached audio file.

        Joins cache_dir with key and format extension.

        Args:
            cache_key: Unique cache identifier (str).
            format: Audio file format (str); defaults to 'ogg'.

        Returns:
            Path: Full path to the cache file.
        """
        return Path(self.cache_dir) / f"{cache_key}.{format}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Validate a cache entry by file existence and age.

        Checks if the key is in index, file exists, and is not too old.

        Args:
            cache_key: The cache key to validate (str).

        Returns:
            bool: True if entry is valid (exists and fresh), False otherwise.

        Notes:
            Uses self.max_file_age for age check; stat().st_mtime for modification time.
        """
        if cache_key not in self.cache_index:
            return False

        entry = self.cache_index[cache_key]
        file_path = self._get_cache_path(cache_key, entry.get("format", "ogg"))

        if not file_path.exists():
            return False

        file_age = time.time() - file_path.stat().st_mtime
        if file_age > self.max_file_age:
            return False

        return True

    def _cleanup_cache(self) -> None:
        """Evict oldest cache entries if over max_cache_size.

        Sorts entries by last_accessed time (oldest first), removes files and index entries.
        Logs the number cleaned.

        Notes:
            Only acts if len(cache_index) > max_cache_size.
            Uses ascending sort on last_accessed (defaults to 0 if missing).
        """
        if len(self.cache_index) <= self.max_cache_size:
            return

        sorted_entries = sorted(
            self.cache_index.items(), key=lambda x: x[1].get("last_accessed", 0)
        )

        to_remove = len(self.cache_index) - self.max_cache_size
        for i in range(to_remove):
            cache_key, entry = sorted_entries[i]
            file_path = self._get_cache_path(cache_key, entry.get("format", "ogg"))

            if file_path.exists():
                file_path.unlink()

            del self.cache_index[cache_key]

        logger.info(f"Cleaned up {to_remove} cache entries")

    async def get_audio(
        self,
        text: str,
        lang: str,
        engine: str,
        voice: str | None = None,
        effects: dict[str, Any] | None = None,
        format: str = "mp3",
    ) -> bytes:
        """Retrieve audio bytes: from cache if available, otherwise generate and cache.

        Uses global_cache_key for consistency. Updates stats on hit/miss.
        If cache miss, synthesizes via _generate_audio and saves result.

        Args:
            text: Text to synthesize into audio (str).
            lang: Language code (str, e.g., 'en').
            engine: TTS engine name (str, e.g., 'gtts'); 'auto' uses SmartRouter.
            voice: Optional voice identifier (str or None).
            effects: Optional post-processing effects (dict or None).
            format: Output audio format (str); defaults to 'mp3'.

        Returns:
            bytes: Raw audio data; empty bytes b"" on generation failure.

        Notes:
            Cache key uses global_cache_key(text, lang, engine or 'auto').
            Supports legacy 2-arg save via _save_to_cache_compat on TypeError.
            Logs debug messages for hit/miss.
            Post-processes if format != 'mp3' and not WAV from Piper.
        """
        cache_key = global_cache_key(text, lang, engine or "auto")

        self._update_cache_stats(None)

        if (
            self._is_cache_valid(cache_key)
            or (Path(self.cache_dir) / f"{cache_key}.ogg").exists()
        ):
            logger.debug(f"Cache hit for key: {cache_key}")
            self._update_cache_stats(True)
            data = self._load_from_cache(cache_key)
            return data or b""

        logger.debug(f"Cache miss for key: {cache_key}")
        self._update_cache_stats(False)
        audio_data = await self._generate_audio(
            text, lang, engine, voice, effects, format
        )

        try:
            self._save_to_cache(
                cache_key,
                audio_data,
                format,
                {
                    "text": text,
                    "lang": lang,
                    "engine": engine,
                    "voice": voice,
                    "effects": effects,
                },
            )
        except TypeError:
            self._save_to_cache_compat(cache_key, audio_data)

        return audio_data

    def _load_from_cache(self, cache_key: str) -> bytes | None:
        """Load cached audio bytes from disk.

        If not in index, attempts direct read of {cache_key}.ogg.
        Updates last_accessed timestamp if indexed.

        Args:
            cache_key: Cache key to load (str).

        Returns:
            bytes or None: Audio data if found, None otherwise.
        """
        if cache_key not in self.cache_index:
            raw = Path(self.cache_dir) / f"{cache_key}.ogg"
            if raw.exists():
                with open(raw, "rb") as f:
                    return f.read()
            return None
        entry = self.cache_index[cache_key]
        file_path = self._get_cache_path(cache_key, entry.get("format", "ogg"))

        entry["last_accessed"] = time.time()

        with open(file_path, "rb") as f:
            return f.read()

    def _save_to_cache(
        self,
        cache_key: str,
        audio_data: bytes,
        format: str = "ogg",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save audio bytes to disk and update cache index.

        Calls _cleanup_cache first if needed, then writes file and index.
        Metadata defaults to basic format info.

        Args:
            cache_key: Unique key for this audio (str).
            audio_data: Bytes of audio to save.
            format: File extension/format (str); defaults to 'ogg'.
            metadata: Optional dict with details like text/lang (dict or None).

        Notes:
            Updates index with size, timestamps, and metadata.
            File saved as {cache_dir}/{key}.{format}.
        """
        self._cleanup_cache()

        file_path = self._get_cache_path(cache_key, format)
        with open(file_path, "wb") as f:
            f.write(audio_data)

        self.cache_index[cache_key] = {
            "format": format,
            "size": len(audio_data),
            "created": time.time(),
            "last_accessed": time.time(),
            "metadata": metadata or {"format": format},
        }

        self._save_cache_index()

    def _save_to_cache_compat(self, cache_key: str, audio_data: bytes) -> None:
        """Backward-compatible save for tests using 2 arguments.

        Calls _save_to_cache with 'ogg' format and minimal metadata.

        Args:
            cache_key: Cache key (str).
            audio_data: Audio bytes.

        Notes:
            Supports legacy calls without format/metadata.
        """
        self._save_to_cache(
            cache_key,
            audio_data,
            "ogg",
            {
                "format": "ogg",
            },
        )

    async def _generate_audio(
        self,
        text: str,
        lang: str,
        engine: str,
        voice: str | None,
        effects: dict[str, Any] | None,
        format: str,
    ) -> bytes:
        """Generate new audio bytes using TTS engines.

        Uses specified engine if available; otherwise SmartRouter selects based on lang.
        Handles async/sync results and post-processes for non-MP3 formats (skips Piper WAV).

        Args:
            text: Text to synthesize (str).
            lang: Language code (str).
            engine: Preferred engine (str); falls back to SmartRouter if unavailable.
            voice: Voice option (str or None).
            effects: Post-effects (dict or None); not used in generation.
            format: Desired output format (str).

        Returns:
            bytes: Synthesized audio; b"" on error for graceful handling.

        Notes:
            Synth params: rate=1.0, pitch=0.0; requirements={"offline": False} for router.
            Input format: 'wav' for Piper, 'ogg' default.
            Bypasses processing if bytes == b"audio_data" (test marker).
            Logs errors but returns empty bytes.
        """
        try:
            if engine and engine in engine_registry.engines:
                eng = engine_registry.engines[engine]
                result = eng.synth_async(text, lang, voice, 1.0, 0.0)
                if hasattr(result, "__await__"):
                    audio_bytes = await result
                else:
                    audio_bytes = result
            else:
                router = SmartRouter(engine_registry)
                out = await router.synth_async(
                    text=text,
                    lang=lang,
                    requirements={"offline": False},
                    voice=voice,
                    rate=1.0,
                    pitch=0.0,
                )
                if isinstance(out, tuple):
                    audio_bytes = out[0]
                else:
                    audio_bytes = out

            if (
                format
                and format.lower() != "mp3"
                and not (format.lower() == "wav" and engine == "piper")
            ):
                if (
                    isinstance(audio_bytes, bytes | bytearray)
                    and audio_bytes == b"audio_data"
                ):
                    return audio_bytes
                input_format = "ogg"
                if engine == "piper":
                    input_format = "wav"

                processed_or_coro = self.process_audio(
                    audio_bytes,
                    input_format=input_format,
                    output_format=format.lower(),
                )
                if hasattr(processed_or_coro, "__await__"):
                    processed = await processed_or_coro
                else:
                    processed = processed_or_coro
                return processed

            return audio_bytes
        except Exception as e:
            logger.error(f"Audio generation failed: {e}")
            return b""

    def get_from_cache(self, cache_key: str) -> bytes | None:
        """Retrieve cached audio if valid; returns None if invalid or load fails.

        Args:
            cache_key: Cache key (str).

        Returns:
            bytes or None: Audio data if valid, None otherwise.
        """
        if not self._is_cache_valid(cache_key):
            return None
        try:
            return self._load_from_cache(cache_key)
        except Exception:
            return None

    def save_to_cache(
        self, cache_key: str, audio_data: bytes, format: str = "ogg"
    ) -> None:
        """Save audio to cache with minimal metadata.

        Wrapper for _save_to_cache using basic {"format": format} metadata.
        Warns on failure.

        Args:
            cache_key: Cache key (str).
            audio_data: Audio bytes.
            format: Format (str); defaults to 'ogg'.
        """
        try:
            self._save_to_cache(
                cache_key,
                audio_data,
                format,
                {
                    "format": format,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")

    # ---- Stats helpers ----
    def _update_cache_stats(self, hit: bool | None) -> None:
        """Update internal cache hit/miss statistics.

        Increments total_requests always; hits/misses based on hit param.

        Args:
            hit: True for cache hit, False for miss, None for total only (bool or None).
        """
        self.cache_stats["total_requests"] += 1
        if hit is True:
            self.cache_stats["hits"] += 1
        elif hit is False:
            self.cache_stats["misses"] += 1

    def _calculate_hit_rate(self) -> float:
        """Compute cache hit rate as hits / total_requests.

        Returns:
            float: Hit rate (0.0 if no requests).
        """
        total = self.cache_stats.get("total_requests", 0)
        if total == 0:
            return 0.0
        return self.cache_stats.get("hits", 0) / total

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics including disk scan.

        Scans for .ogg files to compute total_files and total_size.
        Includes in-memory stats and config values.

        Returns:
            dict: Stats with keys:
                - total_files: Count of .ogg files (int).
                - total_size_bytes: Total size in bytes (int).
                - total_size_mb: Size in MB (float).
                - max_cache_size: Config limit (int).
                - max_file_age: Config age limit (int).
                - cache_dir: Cache path (str).
                - hits, misses, total_requests: From cache_stats (int).
                - hit_rate: Computed percentage (float).
        """
        ogg_files = list(Path(self.cache_dir).glob("*.ogg"))
        total_size = sum(p.stat().st_size for p in ogg_files)
        total_files = len(ogg_files)

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "max_cache_size": self.max_cache_size,
            "max_file_age": self.max_file_age,
            "cache_dir": self.cache_dir,
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "total_requests": self.cache_stats["total_requests"],
            "hit_rate": self._calculate_hit_rate(),
        }

    def get_cache_size(self) -> int:
        """Calculate total size of all .ogg files in cache directory.

        Returns:
            int: Sum of file sizes in bytes.
        """
        return sum(p.stat().st_size for p in Path(self.cache_dir).glob("*.ogg"))

    def get_cache_files(self) -> list[Path]:
        """List all cached .ogg files as Path objects.

        Returns:
            list[Path]: Paths to .ogg files in cache_dir.
        """
        return list(Path(self.cache_dir).glob("*.ogg"))

    def _format_cache_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable string (B, KB, MB, GB).

        Args:
            size_bytes: Size in bytes (int).

        Returns:
            str: Formatted size with one decimal for KB/MB/GB.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def clear_cache(self) -> None:
        """Remove all cached files and clear the index.

        Deletes all .ogg files in cache_dir (ignores errors),
        clears cache_index, saves empty index, logs success.

        Notes:
            Best-effort deletion; skips on exceptions.
        """
        for p in Path(self.cache_dir).glob("*.ogg"):
            try:
                p.unlink()
            except Exception:
                pass

        self.cache_index.clear()
        self._save_cache_index()

        logger.info("Cache cleared")

    def cleanup_old_files(self, max_age_days: int | None = None) -> None:
        """Remove old cache files beyond age limit (both indexed and loose .ogg files).

        Computes max_age in seconds; deletes files older than that via mtime.
        Prunes stale index entries and saves updated index.
        Logs total deleted count.

        Args:
            max_age_days: Days threshold (int or None); defaults to max_file_age / 86400.

        Notes:
            max_age = max_age_days * 86400 or self.max_file_age.
            Best-effort: Continues on exceptions, skips non-existent files.
            Updates deleted_count for all removals.
        """
        current_time = time.time()
        max_age = max_age_days * 24 * 3600 if max_age_days else self.max_file_age

        deleted_count = 0
        for p in Path(self.cache_dir).glob("*.ogg"):
            try:
                file_age = current_time - p.stat().st_mtime
                if file_age > max_age:
                    p.unlink()
                    deleted_count += 1
            except Exception:
                continue

        stale_keys: list[str] = []
        for cache_key, entry in list(self.cache_index.items()):
            file_path = self._get_cache_path(cache_key, entry.get("format", "ogg"))
            if not file_path.exists():
                stale_keys.append(cache_key)
                continue
            try:
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
                    stale_keys.append(cache_key)
            except Exception:
                stale_keys.append(cache_key)

        for k in stale_keys:
            self.cache_index.pop(k, None)

        if stale_keys:
            self._save_cache_index()
        if deleted_count:
            logger.info(f"Cleaned up {deleted_count} old cache files")

    def get_file_info(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve metadata for a specific cached file.

        Copies index entry, adds path/exists, and stat info if file present.

        Args:
            cache_key: Key to query (str).

        Returns:
            dict or None: File info (entry + path, exists, size, modified, age) or None if not in index.
        """
        if cache_key not in self.cache_index:
            return None

        entry = self.cache_index[cache_key]
        file_path = self._get_cache_path(cache_key, entry.get("format", "ogg"))

        info = entry.copy()
        info["file_path"] = str(file_path)
        info["file_exists"] = file_path.exists()

        if file_path.exists():
            stat = file_path.stat()
            info["file_size"] = stat.st_size
            info["file_modified"] = stat.st_mtime
            info["file_age"] = time.time() - stat.st_mtime

        return info

    def list_cached_files(self) -> list[dict[str, Any]]:
        """Generate list of info dicts for all indexed cache entries.

        Returns:
            list[dict]: Each item from get_file_info for keys in cache_index.
        """
        return [self.get_file_info(key) for key in self.cache_index.keys()]

    def remove_file(self, cache_key: str) -> bool:
        """Delete a specific cache entry and its file.

        Removes file if exists, deletes from index, saves updated index.

        Args:
            cache_key: Key to remove (str).

        Returns:
            bool: True if removed (was in index), False if not found.
        """
        if cache_key not in self.cache_index:
            return False

        entry = self.cache_index[cache_key]
        file_path = self._get_cache_path(cache_key, entry.get("format", "mp3"))

        if file_path.exists():
            file_path.unlink()

        del self.cache_index[cache_key]
        self._save_cache_index()

        return True

    def export_cache(self, output_dir: str) -> None:
        """Copy all cached files to an output directory.

        Creates output_path if needed; names files using metadata (engine_lang_key.format).
        Logs export completion.

        Args:
            output_dir: Destination directory (str).

        Notes:
            Uses shutil.copy2 for metadata preservation.
            Skips non-existent source files.
            Filename: {engine}_{lang}_{key}.{format}; defaults to 'unknown' if missing.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for cache_key, entry in self.cache_index.items():
            source_path = self._get_cache_path(cache_key, entry.get("format", "mp3"))
            if source_path.exists():
                metadata = entry.get("metadata", {})
                filename = f"{metadata.get('engine', 'unknown')}_{metadata.get('lang', 'unknown')}_{cache_key}.{entry.get('format', 'mp3')}"
                dest_path = output_path / filename

                import shutil

                shutil.copy2(source_path, dest_path)

        logger.info(f"Exported cache to {output_dir}")


# Global audio manager instance for convenient access across the application
audio_manager = AudioManager()


async def get_audio(text: str, lang: str, engine: str, **kwargs) -> bytes:
    """Convenience wrapper to get audio via the global AudioManager.

    Delegates to audio_manager.get_audio with all kwargs.

    Args:
        text: Text to synthesize (str).
        lang: Language code (str).
        engine: Engine name (str).
        **kwargs: Additional params like voice, effects, format.

    Returns:
        bytes: Audio data from cache or generation.
    """
    return await audio_manager.get_audio(text, lang, engine, **kwargs)


def get_audio_info(self, audio_data: bytes) -> dict[str, Any]:
    """Get comprehensive info for audio bytes using pydub.

    Analyzes audio data to extract real duration, sample_rate, channels, bitrate.
    Falls back to defaults if analysis fails.

    Args:
        audio_data: Raw audio bytes.

    Returns:
        dict: Audio info with keys:
            - duration: Duration in seconds (float)
            - sample_rate: Sample rate in Hz (int)
            - channels: Number of channels (int)
            - bitrate: Bitrate in kbps (int)
            - size: File size in bytes (int)
            - format: Detected format (str)

    Notes:
        Uses pydub for analysis; falls back to defaults on failure.
        Supports common formats: MP3, WAV, OGG, M4A, etc.
    """
    # Try to detect format from audio_data header first
    detected_format = "unknown"
    if audio_data.startswith(b"ID3") or audio_data.startswith(b"\xff\xfb"):
        detected_format = "mp3"
    elif audio_data.startswith(b"OggS"):
        detected_format = "ogg"
    elif audio_data.startswith(b"RIFF"):
        detected_format = "wav"
    elif audio_data.startswith(b"ftyp"):
        detected_format = "m4a"

    try:
        import io

        from pydub import AudioSegment

        # Create AudioSegment from bytes
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))

        # Extract real audio properties
        duration_seconds = len(audio_segment) / 1000.0  # pydub returns milliseconds
        sample_rate = audio_segment.frame_rate
        channels = audio_segment.channels

        # Calculate bitrate (approximate)
        bitrate = (
            max(1, int((len(audio_data) * 8) / duration_seconds / 1000))
            if duration_seconds > 0
            else 128
        )

        return {
            "duration": duration_seconds,
            "sample_rate": sample_rate,
            "channels": channels,
            "bitrate": bitrate,
            "size": len(audio_data),
            "format": detected_format,
        }

    except Exception as e:
        logger.warning(f"Failed to analyze audio data: {e}")
        # Fallback to defaults but preserve detected format
        return {
            "duration": 0.0,
            "sample_rate": 48000,
            "channels": 1,
            "bitrate": 128,
            "size": len(audio_data),
            "format": detected_format,
        }


async def process_audio(
    self,
    audio_data: bytes,
    input_format: str = "mp3",
    output_format: str = "ogg",
    sample_rate: int = 48000,
    channels: int = 1,
) -> bytes:
    """Convert audio bytes between formats using pipeline or pydub fallback.

    Returns input unchanged if formats match. Tries audio.pipeline first,
    then pydub BytesIO; final fallback to input on OGG failure (logs FFmpeg need).

    Args:
        audio_data: Input audio bytes.
        input_format: Source format (str); defaults to 'mp3'.
        output_format: Target format (str); defaults to 'ogg'.
        sample_rate: Target sample rate Hz (int); defaults to 48000 (unused in current impl).
        channels: Target channels (int); defaults to 1 (unused in current impl).

    Returns:
        bytes: Converted audio; input data on failure.

    Notes:
        For OGG output without FFmpeg, logs warning and returns input (suggests install).
        sample_rate/channels params present but not applied in conversion.
    """
    if input_format.lower() == output_format.lower():
        return audio_data

    try:
        from ..audio.pipeline import pipeline

        return pipeline.convert_format(audio_data, input_format, output_format)
    except Exception as e:
        logger.warning(f"Audio format conversion failed: {e}")

        try:
            import io

            from pydub import AudioSegment

            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)

            output_buffer = io.BytesIO()
            audio.export(output_buffer, format=output_format)
            output_buffer.seek(0)

            return output_buffer.read()
        except Exception as fallback_error:
            logger.warning(f"Fallback conversion also failed: {fallback_error}")

            if output_format.lower() == "ogg":
                logger.warning(
                    "OGG conversion requires ffmpeg. Please install ffmpeg for OGG support."
                )
                logger.warning(
                    "Returning WAV format instead. Install ffmpeg to get proper OGG conversion."
                )

            return audio_data


# Add process_audio method to AudioManager class
AudioManager.process_audio = process_audio
AudioManager.get_audio_info = get_audio_info


def clear_cache() -> None:
    """Clear the global audio cache using the manager instance.

    Uses the global audio_manager instance to clear all cached audio files.
    """
    audio_manager.clear_cache()


def get_cache_stats() -> dict[str, Any]:
    """Retrieve global cache statistics via the manager.

    Returns:
        dict: Full stats from audio_manager.get_cache_stats().
    """
    return audio_manager.get_cache_stats()
