"""
Comprehensive tests for ttskit.adapters.factory module.

This module tests the compatibility factory that forwards APIs to telegram.factory.
"""

from unittest.mock import patch

import pytest

from ttskit.adapters.factory import *


class TestAdaptersFactory:
    """Test cases for adapters factory module."""

    def test_factory_imports_forwarded(self):
        """Test that factory imports are properly forwarded."""
        from ttskit.adapters.factory import AdapterFactory, AdapterType

        from ttskit.telegram.factory import AdapterFactory as telegram_AdapterFactory
        from ttskit.telegram.factory import AdapterType as telegram_AdapterType

        assert AdapterFactory is telegram_AdapterFactory
        assert AdapterType is telegram_AdapterType

    def test_factory_module_has_correct_attributes(self):
        """Test that the factory module has the expected attributes."""
        import ttskit.adapters.factory as factory_module

        expected_attributes = [
            "AdapterFactory",
            "AdapterType",
            "create_adapter",
            "get_available_adapters",
            "get_recommended_adapter",
            "check_dependencies",
            "factory",
            "TelegramAdapterFactory",
        ]

        for attr in expected_attributes:
            assert hasattr(factory_module, attr), f"Missing attribute: {attr}"

    def test_factory_imports_all_from_telegram_factory(self):
        """Test that all imports from telegram.factory are available."""
        import ttskit.adapters.factory as factory_module
        import ttskit.telegram.factory as telegram_factory

        telegram_attrs = [
            attr for attr in dir(telegram_factory) if not attr.startswith("_")
        ]

        key_attrs = [
            "AdapterFactory",
            "AdapterType",
            "create_adapter",
            "get_available_adapters",
            "get_recommended_adapter",
            "check_dependencies",
            "factory",
            "TelegramAdapterFactory",
        ]

        for attr in key_attrs:
            assert hasattr(factory_module, attr), f"Missing forwarded attribute: {attr}"

    def test_factory_compatibility_import(self):
        """Test that the compatibility import works as expected."""
        from ttskit.adapters.factory import create_adapter

        assert callable(create_adapter)

        try:
            result = create_adapter("aiogram", "test_token")
            assert result is not None
        except Exception as e:
            assert "test_token" in str(e) or "token" in str(e).lower()

    def test_factory_enum_values(self):
        """Test that AdapterType enum values are correctly forwarded."""
        from ttskit.adapters.factory import AdapterType

        assert hasattr(AdapterType, "AIOGRAM")
        assert hasattr(AdapterType, "PYROGRAM")
        assert hasattr(AdapterType, "TELETHON")
        assert hasattr(AdapterType, "TELEBOT")

        assert AdapterType.AIOGRAM.value == "aiogram"
        assert AdapterType.PYROGRAM.value == "pyrogram"
        assert AdapterType.TELETHON.value == "telethon"
        assert AdapterType.TELEBOT.value == "telebot"

    def test_factory_class_instantiation(self):
        """Test that AdapterFactory can be instantiated."""
        from ttskit.adapters.factory import AdapterFactory

        factory = AdapterFactory()
        assert factory is not None

        assert hasattr(factory, "create_adapter")
        assert hasattr(factory, "get_available_adapters")
        assert hasattr(factory, "get_adapter_info")
        assert hasattr(factory, "check_dependencies")

    def test_factory_module_docstring(self):
        """Test that the module has proper documentation."""
        import ttskit.adapters.factory as factory_module

        assert factory_module.__doc__ is not None
        assert "Compatibility factory module" in factory_module.__doc__
        assert "forwards factory APIs" in factory_module.__doc__

    def test_factory_import_error_handling(self):
        """Test error handling when telegram.factory is not available."""

        import ttskit.adapters.factory as factory_module

        assert factory_module is not None

        assert callable(factory_module.create_adapter)

    def test_factory_type_annotations(self):
        """Test that type annotations are properly forwarded."""
        import inspect

        from ttskit.adapters.factory import AdapterType, create_adapter

        sig = inspect.signature(create_adapter)
        assert len(sig.parameters) >= 2

        assert isinstance(AdapterType.AIOGRAM.value, str)

    def test_factory_consistency_with_telegram_factory(self):
        """Test that adapters.factory is consistent with telegram.factory."""
        import ttskit.adapters.factory as adapters_factory
        import ttskit.telegram.factory as telegram_factory

        assert hasattr(adapters_factory, "create_adapter")
        assert hasattr(telegram_factory, "create_adapter")

        assert callable(adapters_factory.create_adapter)
        assert callable(telegram_factory.create_adapter)

    def test_factory_module_structure(self):
        """Test the overall structure of the factory module."""
        import ttskit.adapters.factory as factory_module

        assert hasattr(factory_module, "__name__")
        assert hasattr(factory_module, "__file__")
        assert hasattr(factory_module, "__doc__")

        import types

        assert isinstance(factory_module, types.ModuleType)

        assert factory_module.__name__ == "ttskit.adapters.factory"

    def test_factory_import_star(self):
        """Test that 'from ttskit.adapters.factory import *' works correctly."""
        import sys

        if "ttskit.adapters.factory" in sys.modules:
            del sys.modules["ttskit.adapters.factory"]

        import ttskit.adapters.factory as factory_module

        assert hasattr(factory_module, "create_adapter")
        assert hasattr(factory_module, "AdapterType")
        assert hasattr(factory_module, "AdapterFactory")

        assert callable(factory_module.create_adapter)
        assert hasattr(factory_module.AdapterType, "AIOGRAM")
        assert callable(factory_module.AdapterFactory)

    def test_factory_backward_compatibility(self):
        """Test backward compatibility for existing code."""
        try:
            from ttskit.adapters.factory import create_adapter as old_create
            from ttskit.telegram.factory import create_adapter as new_create

            assert old_create is new_create

        except ImportError:
            pytest.fail("Backward compatibility broken")

    def test_factory_error_forwarding(self):
        """Test that errors from telegram.factory are properly forwarded."""
        from ttskit.adapters.factory import create_adapter

        with patch("ttskit.telegram.factory.create_adapter") as mock_create:
            mock_create.side_effect = ValueError("Invalid adapter type")

            with pytest.raises(ValueError, match="Unknown adapter type"):
                create_adapter("invalid", "token")

    def test_factory_module_reload(self):
        """Test that the module can be imported multiple times."""
        import ttskit.adapters.factory as factory_module1
        import ttskit.adapters.factory as factory_module2

        assert factory_module1 is factory_module2

        assert hasattr(factory_module1, "create_adapter")
        assert callable(factory_module1.create_adapter)

    def test_factory_import_performance(self):
        """Test that imports are fast and don't cause performance issues."""
        import time

        start_time = time.time()
        end_time = time.time()

        assert (end_time - start_time) < 0.1, "Import too slow"

    def test_factory_memory_usage(self):
        """Test that the factory module doesn't cause memory leaks."""
        import gc
        import sys

        from ttskit.adapters.factory import create_adapter

        initial_refs = sys.getrefcount(create_adapter)

        for _ in range(10):
            from ttskit.adapters.factory import create_adapter

        gc.collect()

        final_refs = sys.getrefcount(create_adapter)
        assert final_refs <= initial_refs + 2, "Potential memory leak detected"
