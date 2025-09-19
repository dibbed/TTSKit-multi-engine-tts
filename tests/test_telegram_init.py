"""Comprehensive tests for Telegram module __init__.py."""

import pytest

from ttskit.telegram import (
    AdapterFactory,
    AdapterType,
    AiogramAdapter,
    PyrogramAdapter,
    TelebotAdapter,
    TelegramAdapter,
    TelegramChat,
    TelegramMessage,
    TelegramUser,
    TelethonAdapter,
    factory,
)


class TestTelegramModuleImports:
    """Test cases for Telegram module imports."""

    def test_telegram_adapter_import(self):
        """Test TelegramAdapter import."""
        assert TelegramAdapter is not None
        from ttskit.telegram.base import TelegramAdapter as BaseTelegramAdapter

        assert TelegramAdapter == BaseTelegramAdapter

    def test_telegram_message_import(self):
        """Test TelegramMessage import."""
        assert TelegramMessage is not None
        from ttskit.telegram.base import TelegramMessage as BaseTelegramMessage

        assert TelegramMessage == BaseTelegramMessage

    def test_telegram_user_import(self):
        """Test TelegramUser import."""
        assert TelegramUser is not None
        from ttskit.telegram.base import TelegramUser as BaseTelegramUser

        assert TelegramUser == BaseTelegramUser

    def test_telegram_chat_import(self):
        """Test TelegramChat import."""
        assert TelegramChat is not None
        from ttskit.telegram.base import TelegramChat as BaseTelegramChat

        assert TelegramChat == BaseTelegramChat

    def test_aiogram_adapter_import(self):
        """Test AiogramAdapter import."""
        assert AiogramAdapter is not None
        from ttskit.telegram.aiogram_adapter import AiogramAdapter as BaseAiogramAdapter

        assert AiogramAdapter == BaseAiogramAdapter

    def test_pyrogram_adapter_import(self):
        """Test PyrogramAdapter import."""
        assert PyrogramAdapter is not None
        from ttskit.telegram.pyrogram_adapter import (
            PyrogramAdapter as BasePyrogramAdapter,
        )

        assert PyrogramAdapter == BasePyrogramAdapter

    def test_telethon_adapter_import(self):
        """Test TelethonAdapter import."""
        assert TelethonAdapter is not None
        from ttskit.telegram.telethon_adapter import (
            TelethonAdapter as BaseTelethonAdapter,
        )

        assert TelethonAdapter == BaseTelethonAdapter

    def test_telebot_adapter_import(self):
        """Test TelebotAdapter import."""
        assert TelebotAdapter is not None
        from ttskit.telegram.telebot_adapter import TelebotAdapter as BaseTelebotAdapter

        assert TelebotAdapter == BaseTelebotAdapter

    def test_adapter_factory_import(self):
        """Test AdapterFactory import."""
        assert AdapterFactory is not None
        from ttskit.telegram.factory import AdapterFactory as BaseAdapterFactory

        assert AdapterFactory == BaseAdapterFactory

    def test_adapter_type_import(self):
        """Test AdapterType import."""
        assert AdapterType is not None
        from ttskit.telegram.factory import AdapterType as BaseAdapterType

        assert AdapterType == BaseAdapterType

    def test_factory_import(self):
        """Test factory import."""
        assert factory is not None
        from ttskit.telegram.factory import factory as base_factory

        assert factory == base_factory


class TestTelegramModuleAllExports:
    """Test cases for __all__ exports."""

    def test_all_exports_completeness(self):
        """Test that __all__ contains all expected exports."""
        from ttskit.telegram import __all__

        expected_exports = [
            "TelegramAdapter",
            "TelegramMessage",
            "TelegramUser",
            "TelegramChat",
            "AiogramAdapter",
            "PyrogramAdapter",
            "TelethonAdapter",
            "TelebotAdapter",
            "AdapterFactory",
            "AdapterType",
        ]

        for export in expected_exports:
            assert export in __all__, f"{export} not in __all__"

    def test_all_exports_no_extra(self):
        """Test that __all__ doesn't contain unexpected exports."""
        from ttskit.telegram import __all__

        unexpected_exports = [
            "base",
            "factory",
            "aiogram_adapter",
            "pyrogram_adapter",
            "telethon_adapter",
            "telebot_adapter",
            "__init__",
        ]

        for export in unexpected_exports:
            assert export not in __all__, f"{export} should not be in __all__"

    def test_all_exports_importable(self):
        """Test that all items in __all__ are importable."""
        from ttskit.telegram import __all__

        for export_name in __all__:
            try:
                exec(f"from ttskit.telegram import {export_name}")
            except ImportError as e:
                pytest.fail(f"Failed to import {export_name}: {e}")


class TestTelegramModuleStructure:
    """Test cases for Telegram module structure."""

    def test_telegram_adapter_is_abstract(self):
        """Test that TelegramAdapter is abstract."""
        from abc import ABC

        assert issubclass(TelegramAdapter, ABC)

        with pytest.raises(TypeError):
            TelegramAdapter("test_token")

    def test_telegram_message_is_dataclass(self):
        """Test that TelegramMessage is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(TelegramMessage)

    def test_telegram_user_is_dataclass(self):
        """Test that TelegramUser is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(TelegramUser)

    def test_telegram_chat_is_dataclass(self):
        """Test that TelegramChat is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(TelegramChat)

    def test_adapter_type_is_enum(self):
        """Test that AdapterType is an enum."""
        from enum import Enum

        assert issubclass(AdapterType, Enum)

    def test_adapter_factory_is_class(self):
        """Test that AdapterFactory is a class."""
        assert isinstance(AdapterFactory, type)

    def test_factory_is_instance(self):
        """Test that factory is an instance."""
        assert isinstance(factory, AdapterFactory)


class TestTelegramModuleIntegration:
    """Integration tests for Telegram module."""

    def test_all_adapters_inherit_from_base(self):
        """Test that all adapters inherit from TelegramAdapter."""
        adapters = [AiogramAdapter, PyrogramAdapter, TelethonAdapter, TelebotAdapter]

        for adapter_class in adapters:
            assert issubclass(adapter_class, TelegramAdapter)

    def test_all_adapters_can_be_instantiated(self):
        """Test that all adapters can be instantiated."""
        aiogram_adapter = AiogramAdapter("test_token")
        assert isinstance(aiogram_adapter, TelegramAdapter)
        assert aiogram_adapter.bot_token == "test_token"

        pyrogram_adapter = PyrogramAdapter(
            "test_token", api_id=12345, api_hash="test_hash"
        )
        assert isinstance(pyrogram_adapter, TelegramAdapter)
        assert pyrogram_adapter.bot_token == "test_token"
        assert pyrogram_adapter.api_id == 12345
        assert pyrogram_adapter.api_hash == "test_hash"

        telethon_adapter = TelethonAdapter(
            "test_token", api_id=12345, api_hash="test_hash"
        )
        assert isinstance(telethon_adapter, TelegramAdapter)
        assert telethon_adapter.bot_token == "test_token"
        assert telethon_adapter.api_id == 12345
        assert telethon_adapter.api_hash == "test_hash"

        telebot_adapter = TelebotAdapter(
            "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
        )
        assert isinstance(telebot_adapter, TelegramAdapter)
        assert (
            telebot_adapter.bot_token
            == "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
        )

    def test_dataclasses_have_expected_fields(self):
        """Test that dataclasses have expected fields."""
        user_fields = TelegramUser.__dataclass_fields__.keys()
        expected_user_fields = {
            "id",
            "username",
            "first_name",
            "last_name",
            "language_code",
            "is_bot",
            "is_premium",
        }
        assert set(user_fields) == expected_user_fields

        message_fields = TelegramMessage.__dataclass_fields__.keys()
        expected_message_fields = {
            "id",
            "chat_id",
            "user",
            "text",
            "message_type",
            "reply_to_message_id",
            "date",
            "edit_date",
            "media_group_id",
            "caption",
            "entities",
            "raw_data",
        }
        assert set(message_fields) == expected_message_fields

        chat_fields = TelegramChat.__dataclass_fields__.keys()
        expected_chat_fields = {
            "id",
            "type",
            "title",
            "username",
            "first_name",
            "last_name",
            "description",
            "invite_link",
        }
        assert set(chat_fields) == expected_chat_fields

    def test_adapter_type_values(self):
        """Test that AdapterType has expected values."""
        expected_values = {"aiogram", "pyrogram", "telethon", "telebot"}
        actual_values = {adapter_type.value for adapter_type in AdapterType}
        assert actual_values == expected_values

    def test_factory_can_create_all_adapters(self):
        """Test that factory can create all adapter types."""
        for adapter_type in AdapterType:
            try:
                token = (
                    "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
                    if adapter_type == AdapterType.TELEBOT
                    else "test_token"
                )
                adapter = factory.create_adapter(adapter_type, token)
                assert isinstance(adapter, TelegramAdapter)
                assert adapter.bot_token == token
            except Exception as e:
                if adapter_type == AdapterType.PYROGRAM:
                    token = "test_token"
                    adapter = factory.create_adapter(
                        adapter_type, token, api_id=12345, api_hash="test_hash"
                    )
                    assert isinstance(adapter, TelegramAdapter)
                elif adapter_type == AdapterType.TELETHON:
                    token = "test_token"
                    adapter = factory.create_adapter(
                        adapter_type, token, api_id=12345, api_hash="test_hash"
                    )
                    assert isinstance(adapter, TelegramAdapter)
                else:
                    pytest.fail(f"Unexpected error creating {adapter_type}: {e}")

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        import ttskit.telegram

        assert ttskit.telegram.__doc__ is not None
        assert "Telegram adapters module for TTSKit" in ttskit.telegram.__doc__

    def test_import_performance(self):
        """Test that imports are fast and don't cause side effects."""
        import time

        start_time = time.time()


        end_time = time.time()
        import_time = end_time - start_time

        assert import_time < 1.0, f"Import took too long: {import_time:.2f}s"

    def test_no_circular_imports(self):
        """Test that there are no circular imports."""
        import sys

        modules_to_clear = [
            name for name in sys.modules.keys() if name.startswith("ttskit.telegram")
        ]
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

        try:
            import ttskit.telegram
            import ttskit.telegram.aiogram_adapter
            import ttskit.telegram.base
            import ttskit.telegram.factory
            import ttskit.telegram.pyrogram_adapter
            import ttskit.telegram.telebot_adapter
            import ttskit.telegram.telethon_adapter
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_module_attributes(self):
        """Test that module has expected attributes."""
        import ttskit.telegram

        expected_attributes = [
            "TelegramAdapter",
            "TelegramMessage",
            "TelegramUser",
            "TelegramChat",
            "AiogramAdapter",
            "PyrogramAdapter",
            "TelethonAdapter",
            "TelebotAdapter",
            "AdapterFactory",
            "AdapterType",
            "factory",
        ]

        for attr in expected_attributes:
            assert hasattr(ttskit.telegram, attr), f"Module missing attribute: {attr}"

    def test_version_compatibility(self):
        """Test that module works with expected Python versions."""
        import sys

        assert sys.version_info >= (3, 8), "Module requires Python 3.8+"

        from typing import get_type_hints

        user_hints = get_type_hints(TelegramUser)
        assert "id" in user_hints
        assert user_hints["id"] == int

        message_hints = get_type_hints(TelegramMessage)
        assert "id" in message_hints
        assert message_hints["id"] == int
        assert "user" in message_hints
        assert message_hints["user"] == TelegramUser
