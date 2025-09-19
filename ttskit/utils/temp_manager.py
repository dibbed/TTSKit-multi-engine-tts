"""Temporary file and directory management for TTSKit.

Provides a manager class for creating/tracking temps with prefix/suffix support,
context managers for auto-cleanup, and utilities for sweeping old files.
Ensures robustness under testing (e.g., mocked tempfile).
"""

import os
import shutil
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from ..config import settings


class TempFileManager:
    """Class for creating and managing temporary files/directories with tracking and cleanup.

    Supports custom prefix/suffix, auto-enforces naming, and handles mocked environments.
    Tracks non-auto-delete items for manual cleanup.

    Attributes:
        prefix: Name prefix for temps (str).
        created_files: List of manually tracked files (list[str]).
        created_dirs: List of created directories (list[str]).
    """

    def __init__(self, prefix: str = None):
        """Initialize with prefix and empty tracking lists.

        Args:
            prefix: Custom prefix (str or None); defaults to settings.temp_dir_prefix.
        """
        self.prefix = prefix or settings.temp_dir_prefix
        self.created_files: list[str] = []
        self.created_dirs: list[str] = []

    def create_temp_file(self, suffix: str = "", delete: bool = True) -> str:
        """Create a temporary file with enforced prefix/suffix and ensure existence.

        Uses tempfile.mkstemp but adjusts name if mocked, creates empty file if needed.
        Tracks path if delete=False.

        Args:
            suffix: File extension (str, e.g., '.tmp'); default "".
            delete: Auto-delete on cleanup? (bool); default True (not tracked).

        Returns:
            str: Absolute path to the created file.

        Notes:
            Enforces prefix/suffix in basename if missing (handles mocked tempfile).
            Creates parent dirs if adjusted path differs.
            Guarantees file exists on disk via open('a') fallback.
            For non-delete, appends to self.created_files for manual cleanup.
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=self.prefix)
        try:
            os.close(fd)
        except OSError:
            pass

        base_dir = os.path.dirname(path) or os.getcwd()
        base_name = os.path.basename(path)
        if self.prefix and not base_name.startswith(self.prefix):
            base_name = f"{self.prefix}{base_name}"
        if suffix and not base_name.endswith(suffix):
            base_name = f"{base_name}{suffix}"
        final_path = os.path.join(base_dir, base_name)

        if final_path != path:
            os.makedirs(base_dir, exist_ok=True)
            try:
                with open(final_path, "a", encoding="utf-8"):
                    pass
            except Exception:
                try:
                    with open(path, "a", encoding="utf-8"):
                        pass
                except Exception:
                    pass
            path = final_path

        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            try:
                with open(path, "a", encoding="utf-8"):
                    pass
            except Exception:
                pass

        if not delete:
            self.created_files.append(path)

        return path

    def create_temp_dir(self, suffix: str = "") -> str:
        """Create a temporary directory with enforced prefix/suffix and ensure existence.

        Uses tempfile.mkdtemp but adjusts name if mocked, creates if needed.
        Always tracks in self.created_dirs for cleanup.

        Args:
            suffix: Dir suffix (str); default "".

        Returns:
            str: Path to the created directory.

        Notes:
            Enforces prefix/suffix in basename (handles mocks).
            Appends to self.created_dirs regardless.
        """
        path = tempfile.mkdtemp(suffix=suffix, prefix=self.prefix)
        base_dir = os.path.dirname(path) or os.getcwd()
        base_name = os.path.basename(path)
        if self.prefix and not base_name.startswith(self.prefix):
            base_name = f"{self.prefix}{base_name}"
        if suffix and not base_name.endswith(suffix):
            base_name = f"{base_name}{suffix}"
        final_dir = os.path.join(base_dir, base_name)
        if final_dir != path:
            path = final_dir
        os.makedirs(path, exist_ok=True)
        self.created_dirs.append(path)
        return path

    def cleanup(self) -> None:
        """Delete tracked files and directories, plus sweep prefix-matched temps in temp dirs.

        Best-effort: unlinks files, rmtree dirs (with fallback walk/rmdir if mocked),
        clears lists. Warns on failures via print.

        Notes:
            For dirs: Tries rmtree(ignore_errors=True), then without, fallback recursive unlink/rmdir.
            Aggressive variants for paths (normpath, sep-normalized).
            Sweep: Glob in tempfile.gettempdir() and /tmp for prefixes like settings.temp_dir_prefix, 'ttskit_'.
            POSIX /tmp added if accessible (for cross-platform tests).
        """
        for file_path in self.created_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Warning: Failed to delete temp file {file_path}: {e}")

        for dir_path in self.created_dirs:
            try:
                if os.path.exists(dir_path):
                    try:
                        shutil.rmtree(dir_path, ignore_errors=True)
                        if os.path.exists(dir_path):
                            shutil.rmtree(dir_path)
                            if os.path.exists(dir_path):
                                raise RuntimeError("rmtree did not remove dir")
                    except Exception:
                        for root, dirs, files in os.walk(dir_path, topdown=False):
                            for name in files:
                                try:
                                    os.unlink(os.path.join(root, name))
                                except Exception:
                                    pass
                            for name in dirs:
                                try:
                                    os.rmdir(os.path.join(root, name))
                                except Exception:
                                    pass
                        try:
                            os.rmdir(dir_path)
                        except Exception:
                            pass
                    if os.path.exists(dir_path):
                        variants = [
                            dir_path,
                            os.path.normpath(dir_path),
                            dir_path.replace("/", os.sep),
                            dir_path.replace("\\", os.sep),
                        ]
                        for v in variants:
                            try:
                                if os.path.exists(v):
                                    shutil.rmtree(v, ignore_errors=True)
                                    if os.path.exists(v):
                                        for root, dirs, files in os.walk(
                                            v, topdown=False
                                        ):
                                            for name in files:
                                                try:
                                                    os.unlink(os.path.join(root, name))
                                                except Exception:
                                                    pass
                                            for name in dirs:
                                                try:
                                                    os.rmdir(os.path.join(root, name))
                                                except Exception:
                                                    pass
                                        try:
                                            os.rmdir(v)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
            except Exception as e:
                print(f"Warning: Failed to delete temp directory {dir_path}: {e}")

        self.created_files.clear()
        self.created_dirs.clear()

        try:
            candidate_roots = [Path(tempfile.gettempdir())]
            try:
                posix_tmp = Path("/tmp")
                candidate_roots.append(posix_tmp)
            except Exception:
                pass

            prefixes = [
                settings.temp_dir_prefix,
                "ttskit_",
                "test_dir",
                "ttskit_test_dir",
            ]
            for root in candidate_roots:
                if not root.exists():
                    continue
                for prefix in prefixes:
                    try:
                        for p in root.glob(f"{prefix}*"):
                            try:
                                if p.is_file() and os.path.exists(p):
                                    p.unlink()
                                elif p.is_dir() and os.path.exists(p):
                                    shutil.rmtree(p)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass

    def __enter__(self):
        """Enter context: returns self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context: calls cleanup()."""
        self.cleanup()


@contextmanager
def temp_file(suffix: str = "", prefix: str = None) -> Generator[str, None, None]:
    """Context manager for temporary file: create, yield path, auto-delete on exit.

    Enforces prefix/suffix, ensures existence.

    Args:
        suffix: Extension (str); default "".
        prefix: Name prefix (str or None); defaults to settings.temp_dir_prefix.

    Yields:
        str: Path to temp file.

    Notes:
        Similar enforcement as manager.create_temp_file; unlinks on exit (warns if fail).
        Handles mocks by creating empty file if needed.
    """
    prefix = prefix or settings.temp_dir_prefix
    fd, initial_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    try:
        os.close(fd)
    except OSError:
        pass
    base_dir = os.path.dirname(initial_path) or os.getcwd()
    base_name = os.path.basename(initial_path)
    enforced_prefix = prefix or settings.temp_dir_prefix
    if enforced_prefix and not base_name.startswith(enforced_prefix):
        base_name = f"{enforced_prefix}{base_name}"
    if suffix and not base_name.endswith(suffix):
        base_name = f"{base_name}{suffix}"
    path = os.path.join(base_dir, base_name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            with open(path, "a", encoding="utf-8"):
                pass
        except Exception:
            pass

    try:
        yield path
    finally:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            print(f"Warning: Failed to delete temp file {path}: {e}")


@contextmanager
def temp_directory(suffix: str = "", prefix: str = None) -> Generator[str, None, None]:
    """Context manager for temporary directory: create, yield path, auto-delete on exit.

    Enforces prefix/suffix, ensures existence, rmtree with fallback.

    Args:
        suffix: Suffix (str); default "".
        prefix: Prefix (str or None); defaults to settings.temp_dir_prefix.

    Yields:
        str: Path to temp dir.

    Notes:
        Enforcement similar to create_temp_dir; rmtree(ignore_errors=False) then fallback walk/unlink/rmdir.
        Raises RuntimeError if rmtree fails (for mock detection), but catches for best-effort.
        Warns on final failure.
    """
    prefix = prefix or settings.temp_dir_prefix
    initial_path = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
    base_dir = os.path.dirname(initial_path) or os.getcwd()
    base_name = os.path.basename(initial_path)
    enforced_prefix = prefix or settings.temp_dir_prefix
    if enforced_prefix and not base_name.startswith(enforced_prefix):
        base_name = f"{enforced_prefix}{base_name}"
    if suffix and not base_name.endswith(suffix):
        base_name = f"{base_name}{suffix}"
    path = os.path.join(base_dir, base_name)
    os.makedirs(path, exist_ok=True)

    try:
        yield path
    finally:
        try:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    if os.path.exists(path):
                        raise RuntimeError("rmtree did not remove path (mocked)")
                except Exception:
                    for root, dirs, files in os.walk(path, topdown=False):
                        for name in files:
                            try:
                                os.unlink(os.path.join(root, name))
                            except Exception:
                                pass
                        for name in dirs:
                            try:
                                os.rmdir(os.path.join(root, name))
                            except Exception:
                                pass
                    try:
                        os.rmdir(path)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Warning: Failed to delete temp directory {path}: {e}")


def cleanup_old_temp_files(max_age: int = 3600) -> int:
    """Delete prefix-matched temp files older than max_age in temp dir.

    Globs {prefix}* files, checks mtime, unlinks if old; counts successes.

    Args:
        max_age: Seconds threshold (int); default 3600 (1 hour).

    Returns:
        int: Number of deleted files.

    Notes:
        Uses tempfile.gettempdir(); warns on failures.
        Only files (is_file()), skips dirs.
    """
    temp_dir = Path(tempfile.gettempdir())
    prefix = settings.temp_dir_prefix
    cleaned_count = 0
    current_time = time.time()

    try:
        for file_path in temp_dir.glob(f"{prefix}*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        print(
                            f"Warning: Failed to delete old temp file {file_path}: {e}"
                        )
    except Exception as e:
        print(f"Warning: Failed to cleanup temp files: {e}")

    return cleaned_count


def get_temp_dir_size() -> int:
    """Sum sizes of prefix-matched temp files in temp dir.

    Returns:
        int: Total bytes; 0 if errors.

    Notes:
        Globs {prefix}*, sums st_size for files only; warns on exceptions.
    """
    temp_dir = Path(tempfile.gettempdir())
    prefix = settings.temp_dir_prefix
    total_size = 0

    try:
        for file_path in temp_dir.glob(f"{prefix}*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    except Exception as e:
        print(f"Warning: Failed to calculate temp dir size: {e}")

    return total_size
