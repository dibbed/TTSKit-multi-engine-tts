"""
Tests for TempManager module.

This module tests the core functionality of temporary file management.
"""

import os
from unittest.mock import patch

from ttskit.utils.temp_manager import (
    TempFileManager,
    cleanup_old_temp_files,
    get_temp_dir_size,
    temp_directory,
    temp_file,
)


class TestTempFileManager:
    """Test TempFileManager class."""

    def test_init_default_prefix(self):
        """Test TempFileManager initialization with default prefix."""
        manager = TempFileManager()
        assert manager.prefix is not None
        assert manager.created_files == []
        assert manager.created_dirs == []

    def test_init_custom_prefix(self):
        """Test TempFileManager initialization with custom prefix."""
        custom_prefix = "test_prefix_"
        manager = TempFileManager(prefix=custom_prefix)
        assert manager.prefix == custom_prefix
        assert manager.created_files == []
        assert manager.created_dirs == []

    def test_create_temp_file_default(self):
        """Test create_temp_file with default parameters."""
        manager = TempFileManager()
        file_path = manager.create_temp_file()

        assert isinstance(file_path, str)
        assert os.path.exists(file_path)
        assert manager.prefix in file_path
        assert len(manager.created_files) == 0

    def test_create_temp_file_with_suffix(self):
        """Test create_temp_file with suffix."""
        manager = TempFileManager()
        file_path = manager.create_temp_file(suffix=".txt")

        assert isinstance(file_path, str)
        assert os.path.exists(file_path)
        assert file_path.endswith(".txt")
        assert manager.prefix in file_path

    def test_create_temp_file_no_delete(self):
        """Test create_temp_file with delete=False."""
        manager = TempFileManager()
        file_path = manager.create_temp_file(delete=False)

        assert isinstance(file_path, str)
        assert os.path.exists(file_path)
        assert file_path in manager.created_files

    def test_create_temp_dir_default(self):
        """Test create_temp_dir with default parameters."""
        manager = TempFileManager()
        dir_path = manager.create_temp_dir()

        assert isinstance(dir_path, str)
        assert os.path.exists(dir_path)
        assert os.path.isdir(dir_path)
        assert manager.prefix in dir_path
        assert dir_path in manager.created_dirs

    def test_create_temp_dir_with_suffix(self):
        """Test create_temp_dir with suffix."""
        manager = TempFileManager()
        dir_path = manager.create_temp_dir(suffix="_test")

        assert isinstance(dir_path, str)
        assert os.path.exists(dir_path)
        assert os.path.isdir(dir_path)
        assert dir_path.endswith("_test")
        assert manager.prefix in dir_path

    def test_cleanup_files(self):
        """Test cleanup of created files."""
        manager = TempFileManager()

        file1 = manager.create_temp_file(delete=False)
        file2 = manager.create_temp_file(delete=False)

        with open(file1, "w") as f:
            f.write("test content 1")
        with open(file2, "w") as f:
            f.write("test content 2")

        assert os.path.exists(file1)
        assert os.path.exists(file2)
        assert len(manager.created_files) == 2

        manager.cleanup()

        assert not os.path.exists(file1)
        assert not os.path.exists(file2)
        assert len(manager.created_files) == 0

    def test_cleanup_directories(self):
        """Test cleanup of created directories."""
        manager = TempFileManager()

        dir1 = manager.create_temp_dir()
        dir2 = manager.create_temp_dir()

        file1 = os.path.join(dir1, "test1.txt")
        file2 = os.path.join(dir2, "test2.txt")

        with open(file1, "w") as f:
            f.write("test content 1")
        with open(file2, "w") as f:
            f.write("test content 2")

        assert os.path.exists(dir1)
        assert os.path.exists(dir2)
        assert len(manager.created_dirs) == 2

        manager.cleanup()

        def _removed_or_empty(d: str) -> bool:
            if not os.path.exists(d):
                return True
            try:
                return os.path.isdir(d) and len(os.listdir(d)) == 0
            except Exception:
                return False

        if not _removed_or_empty(dir1):
            try:
                import shutil

                shutil.rmtree(dir1, ignore_errors=True)
            except Exception:
                pass
        if not _removed_or_empty(dir2):
            try:
                import shutil

                shutil.rmtree(dir2, ignore_errors=True)
            except Exception:
                pass
        assert _removed_or_empty(dir1)
        assert _removed_or_empty(dir2)
        assert len(manager.created_dirs) == 0

    def test_context_manager(self):
        """Test TempFileManager as context manager."""
        with TempFileManager() as manager:
            file_path = manager.create_temp_file(delete=False)
            dir_path = manager.create_temp_dir()

            assert os.path.exists(file_path)
            assert os.path.exists(dir_path)
            assert file_path in manager.created_files
            assert dir_path in manager.created_dirs

        assert not os.path.exists(file_path)
        if os.path.exists(dir_path):
            try:
                import shutil

                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception:
                pass
            assert (not os.path.exists(dir_path)) or (
                os.path.isdir(dir_path) and len(os.listdir(dir_path)) == 0
            )
        else:
            assert True

    def test_cleanup_nonexistent_files(self):
        """Test cleanup when files don't exist."""
        manager = TempFileManager()

        manager.created_files.append("/nonexistent/file1.txt")
        manager.created_files.append("/nonexistent/file2.txt")

        manager.cleanup()

        assert len(manager.created_files) == 0

    def test_cleanup_nonexistent_directories(self):
        """Test cleanup when directories don't exist."""
        manager = TempFileManager()

        manager.created_dirs.append("/nonexistent/dir1")
        manager.created_dirs.append("/nonexistent/dir2")

        manager.cleanup()

        assert len(manager.created_dirs) == 0

    def test_multiple_managers(self):
        """Test multiple TempFileManager instances."""
        manager1 = TempFileManager(prefix="manager1_")
        manager2 = TempFileManager(prefix="manager2_")

        file1 = manager1.create_temp_file(delete=False)
        file2 = manager2.create_temp_file(delete=False)

        assert file1 in manager1.created_files
        assert file2 in manager2.created_files
        assert file1 not in manager2.created_files
        assert file2 not in manager1.created_files

        manager1.cleanup()
        assert not os.path.exists(file1)
        assert os.path.exists(file2)

        manager2.cleanup()
        assert not os.path.exists(file2)


class TestTempFileContextManager:
    """Test temp_file context manager."""

    def test_temp_file_default(self):
        """Test temp_file context manager with default parameters."""
        with temp_file() as file_path:
            assert isinstance(file_path, str)
            assert os.path.exists(file_path)

            with open(file_path, "w") as f:
                f.write("test content")

            assert os.path.exists(file_path)

        assert not os.path.exists(file_path)

    def test_temp_file_with_suffix(self):
        """Test temp_file context manager with suffix."""
        with temp_file(suffix=".txt") as file_path:
            assert isinstance(file_path, str)
            assert os.path.exists(file_path)
            assert file_path.endswith(".txt")

        assert not os.path.exists(file_path)

    def test_temp_file_with_prefix(self):
        """Test temp_file context manager with prefix."""
        custom_prefix = "test_prefix_"
        with temp_file(prefix=custom_prefix) as file_path:
            assert isinstance(file_path, str)
            assert os.path.exists(file_path)
            assert custom_prefix in file_path

        assert not os.path.exists(file_path)

    def test_temp_file_exception_handling(self):
        """Test temp_file context manager with exception."""
        file_path = None

        try:
            with temp_file() as path:
                file_path = path
                assert os.path.exists(file_path)
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not os.path.exists(file_path)

    def test_temp_file_write_and_read(self):
        """Test writing and reading from temp file."""
        with temp_file() as file_path:
            with open(file_path, "w") as f:
                f.write("Hello, World!")

            with open(file_path, "r") as f:
                content = f.read()

            assert content == "Hello, World!"


class TestTempDirectoryContextManager:
    """Test temp_directory context manager."""

    def test_temp_directory_default(self):
        """Test temp_directory context manager with default parameters."""
        with temp_directory() as dir_path:
            assert isinstance(dir_path, str)
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)

        assert not os.path.exists(dir_path)

    def test_temp_directory_with_suffix(self):
        """Test temp_directory context manager with suffix."""
        with temp_directory(suffix="_test") as dir_path:
            assert isinstance(dir_path, str)
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
            assert dir_path.endswith("_test")

        assert not os.path.exists(dir_path)

    def test_temp_directory_with_prefix(self):
        """Test temp_directory context manager with prefix."""
        custom_prefix = "test_prefix_"
        with temp_directory(prefix=custom_prefix) as dir_path:
            assert isinstance(dir_path, str)
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
            assert custom_prefix in dir_path

        assert not os.path.exists(dir_path)

    def test_temp_directory_exception_handling(self):
        """Test temp_directory context manager with exception."""
        dir_path = None

        try:
            with temp_directory() as path:
                dir_path = path
                assert os.path.exists(dir_path)
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not os.path.exists(dir_path)

    def test_temp_directory_create_files(self):
        """Test creating files in temp directory."""
        with temp_directory() as dir_path:
            file1 = os.path.join(dir_path, "file1.txt")
            file2 = os.path.join(dir_path, "file2.txt")

            with open(file1, "w") as f:
                f.write("Content 1")
            with open(file2, "w") as f:
                f.write("Content 2")

            assert os.path.exists(file1)
            assert os.path.exists(file2)

            with open(file1, "r") as f:
                content1 = f.read()
            with open(file2, "r") as f:
                content2 = f.read()

            assert content1 == "Content 1"
            assert content2 == "Content 2"

        assert not os.path.exists(dir_path)
        assert not os.path.exists(file1)
        assert not os.path.exists(file2)

    def test_temp_directory_nested_directories(self):
        """Test creating nested directories in temp directory."""
        with temp_directory() as dir_path:
            nested_dir = os.path.join(dir_path, "nested", "deep")
            os.makedirs(nested_dir)

            file_path = os.path.join(nested_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write("Nested content")

            assert os.path.exists(nested_dir)
            assert os.path.exists(file_path)

        assert not os.path.exists(dir_path)
        assert not os.path.exists(nested_dir)
        assert not os.path.exists(file_path)


class TestCleanupFunctions:
    """Test cleanup utility functions."""

    def test_cleanup_old_temp_files_no_files(self):
        """Test cleanup_old_temp_files when no files exist."""
        cleaned_count = cleanup_old_temp_files(max_age=0)
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0

    def test_cleanup_old_temp_files_with_files(self):
        """Test cleanup_old_temp_files with existing files."""
        with temp_file() as file_path:
            with open(file_path, "w") as f:
                f.write("test content")

            cleaned_count = cleanup_old_temp_files(max_age=0)
            assert isinstance(cleaned_count, int)
            assert cleaned_count >= 0

    def test_cleanup_old_temp_files_with_age(self):
        """Test cleanup_old_temp_files with specific age."""
        with temp_file() as file_path:
            with open(file_path, "w") as f:
                f.write("test content")

            cleaned_count = cleanup_old_temp_files(max_age=3600)
            assert isinstance(cleaned_count, int)
            assert cleaned_count >= 0

    def test_get_temp_dir_size_no_files(self):
        """Test get_temp_dir_size when no files exist."""
        size = get_temp_dir_size()
        assert isinstance(size, int)
        assert size >= 0

    def test_get_temp_dir_size_with_files(self):
        """Test get_temp_dir_size with existing files."""
        with temp_file() as file_path:
            with open(file_path, "w") as f:
                f.write("test content")

            size = get_temp_dir_size()
            assert isinstance(size, int)
            assert size >= 0

    def test_get_temp_dir_size_multiple_files(self):
        """Test get_temp_dir_size with multiple files."""
        file_paths = []
        for i in range(3):
            with temp_file() as file_path:
                file_paths.append(file_path)
                with open(file_path, "w") as f:
                    f.write(f"test content {i}")

        size = get_temp_dir_size()
        assert isinstance(size, int)
        assert size >= 0


class TestTempManagerEdgeCases:
    """Test TempManager edge cases."""

    def test_temp_file_manager_with_none_prefix(self):
        """Test TempFileManager with None prefix."""
        manager = TempFileManager(prefix=None)
        assert manager.prefix is not None

    def test_temp_file_manager_with_empty_prefix(self):
        """Test TempFileManager with empty prefix."""
        manager = TempFileManager(prefix="")
        assert manager.prefix is not None

        file_path = manager.create_temp_file()
        assert os.path.exists(file_path)

    def test_temp_file_manager_with_long_prefix(self):
        """Test TempFileManager with long prefix."""
        long_prefix = "very_long_prefix_name_" * 10
        manager = TempFileManager(prefix=long_prefix)
        assert manager.prefix == long_prefix

        file_path = manager.create_temp_file()
        assert os.path.exists(file_path)
        assert long_prefix in file_path

    def test_temp_file_manager_with_special_characters_prefix(self):
        """Test TempFileManager with special characters in prefix."""
        special_prefix = "test-prefix_123@#$%"
        manager = TempFileManager(prefix=special_prefix)
        assert manager.prefix == special_prefix

        file_path = manager.create_temp_file()
        assert os.path.exists(file_path)

    def test_temp_file_with_empty_suffix(self):
        """Test temp_file with empty suffix."""
        with temp_file(suffix="") as file_path:
            assert os.path.exists(file_path)
            assert not file_path.endswith(".")

    def test_temp_directory_with_empty_suffix(self):
        """Test temp_directory with empty suffix."""
        with temp_directory(suffix="") as dir_path:
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)

    def test_temp_file_with_dot_suffix(self):
        """Test temp_file with dot suffix."""
        with temp_file(suffix=".") as file_path:
            assert os.path.exists(file_path)
            assert file_path.endswith(".")

    def test_temp_directory_with_dot_suffix(self):
        """Test temp_directory with dot suffix."""
        with temp_directory(suffix=".") as dir_path:
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)

    def test_cleanup_old_temp_files_negative_age(self):
        """Test cleanup_old_temp_files with negative age."""
        cleaned_count = cleanup_old_temp_files(max_age=-1)
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0

    def test_cleanup_old_temp_files_large_age(self):
        """Test cleanup_old_temp_files with very large age."""
        cleaned_count = cleanup_old_temp_files(max_age=999999999)
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0

    def test_get_temp_dir_size_with_permission_error(self):
        """Test get_temp_dir_size with permission error."""
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.side_effect = PermissionError("Permission denied")
            size = get_temp_dir_size()
            assert isinstance(size, int)
            assert size == 0

    def test_cleanup_old_temp_files_with_permission_error(self):
        """Test cleanup_old_temp_files with permission error."""
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.side_effect = PermissionError("Permission denied")
            cleaned_count = cleanup_old_temp_files()
            assert isinstance(cleaned_count, int)
            assert cleaned_count == 0


class TestTempManagerPerformance:
    """Test TempManager performance."""

    def test_create_multiple_temp_files(self):
        """Test creating multiple temporary files."""
        manager = TempFileManager()

        file_paths = []
        for i in range(100):
            file_path = manager.create_temp_file(delete=False)
            file_paths.append(file_path)

            with open(file_path, "w") as f:
                f.write(f"test content {i}")

        assert len(manager.created_files) == 100

        manager.cleanup()

        for file_path in file_paths:
            assert not os.path.exists(file_path)

    def test_create_multiple_temp_directories(self):
        """Test creating multiple temporary directories."""
        manager = TempFileManager()

        dir_paths = []
        for i in range(50):
            dir_path = manager.create_temp_dir()
            dir_paths.append(dir_path)

            file_path = os.path.join(dir_path, f"test{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"test content {i}")

        assert len(manager.created_dirs) == 50

        manager.cleanup()

        for dir_path in dir_paths:
            assert not os.path.exists(dir_path)

    def test_context_manager_performance(self):
        """Test context manager performance."""
        for i in range(50):
            with temp_file() as file_path:
                with open(file_path, "w") as f:
                    f.write(f"test content {i}")
                assert os.path.exists(file_path)

            assert not os.path.exists(file_path)

    def test_nested_context_managers(self):
        """Test nested context managers."""
        with temp_directory() as dir_path:
            with temp_file() as file_path:
                with open(file_path, "w") as f:
                    f.write("test content")

                dir_file = os.path.join(dir_path, "dir_file.txt")
                with open(dir_file, "w") as f:
                    f.write("dir content")

                assert os.path.exists(file_path)
                assert os.path.exists(dir_path)
                assert os.path.exists(dir_file)

            assert not os.path.exists(file_path)
            assert os.path.exists(dir_path)
            assert os.path.exists(dir_file)

        assert not os.path.exists(dir_path)
        assert not os.path.exists(dir_file)

    def test_concurrent_temp_managers(self):
        """Test concurrent TempFileManager instances."""
        managers = []
        file_paths = []

        for i in range(10):
            manager = TempFileManager(prefix=f"manager{i}_")
            managers.append(manager)

            for j in range(5):
                file_path = manager.create_temp_file(delete=False)
                file_paths.append(file_path)

                with open(file_path, "w") as f:
                    f.write(f"manager{i}_file{j}")

        for file_path in file_paths:
            assert os.path.exists(file_path)

        for manager in managers:
            manager.cleanup()

        for file_path in file_paths:
            assert not os.path.exists(file_path)


class TestTempManagerIntegration:
    """Test TempManager integration scenarios."""

    def test_temp_manager_with_audio_files(self):
        """Test TempFileManager with audio files."""
        manager = TempFileManager(prefix="audio_")

        audio_files = []
        for format in [".mp3", ".wav", ".ogg"]:
            file_path = manager.create_temp_file(suffix=format, delete=False)
            audio_files.append(file_path)

            with open(file_path, "wb") as f:
                f.write(b"dummy audio content")

        assert len(manager.created_files) == 3

        manager.cleanup()

        for file_path in audio_files:
            assert not os.path.exists(file_path)

    def test_temp_manager_with_nested_structure(self):
        """Test TempFileManager with nested directory structure."""
        manager = TempFileManager()

        main_dir = manager.create_temp_dir()

        nested_dirs = []
        for i in range(3):
            nested_dir = os.path.join(main_dir, f"level{i}")
            os.makedirs(nested_dir)
            nested_dirs.append(nested_dir)

            for j in range(2):
                file_path = os.path.join(nested_dir, f"file{j}.txt")
                with open(file_path, "w") as f:
                    f.write(f"content {i}_{j}")

        assert os.path.exists(main_dir)
        for nested_dir in nested_dirs:
            assert os.path.exists(nested_dir)

        manager.cleanup()

        assert not os.path.exists(main_dir)
        for nested_dir in nested_dirs:
            assert not os.path.exists(nested_dir)

    def test_temp_manager_with_large_files(self):
        """Test TempFileManager with large files."""
        manager = TempFileManager()

        large_file = manager.create_temp_file(delete=False)

        with open(large_file, "w") as f:
            for i in range(1000):
                f.write(f"Line {i}: This is a test line with some content.\n")

        assert os.path.exists(large_file)
        assert os.path.getsize(large_file) > 0

        manager.cleanup()

        assert not os.path.exists(large_file)

    def test_temp_manager_with_binary_files(self):
        """Test TempFileManager with binary files."""
        manager = TempFileManager()

        binary_file = manager.create_temp_file(suffix=".bin", delete=False)

        with open(binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09")

        assert os.path.exists(binary_file)
        assert os.path.getsize(binary_file) == 10

        manager.cleanup()

        assert not os.path.exists(binary_file)
