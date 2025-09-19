"""Comprehensive tests for Telegram factory module."""

from unittest.mock import Mock, patch

import pytest

from ttskit.telegram.factory import (
    AdapterFactory,
    AdapterType,
    TelegramAdapterFactory,
    check_dependencies,
    create_adapter,
    factory,
    get_available_adapters,
    get_recommended_adapter,
)


class TestAdapterType:
    """Test cases for AdapterType enum."""

    def test_adapter_type_values(self):
        """Test AdapterType enum values."""
        assert AdapterType.AIOGRAM.value == "aiogram"
        assert AdapterType.PYROGRAM.value == "pyrogram"
        assert AdapterType.TELETHON.value == "telethon"
        assert AdapterType.TELEBOT.value == "telebot"

    def test_adapter_type_enumeration(self):
        """Test AdapterType enumeration."""
        types = list(AdapterType)
        assert len(types) == 4
        assert AdapterType.AIOGRAM in types
        assert AdapterType.PYROGRAM in types
        assert AdapterType.TELETHON in types
        assert AdapterType.TELEBOT in types

    def test_adapter_type_from_value(self):
        """Test creating AdapterType from value."""
        assert AdapterType("aiogram") == AdapterType.AIOGRAM
        assert AdapterType("pyrogram") == AdapterType.PYROGRAM
        assert AdapterType("telethon") == AdapterType.TELETHON
        assert AdapterType("telebot") == AdapterType.TELEBOT

    def test_adapter_type_invalid_value(self):
        """Test creating AdapterType from invalid value."""
        with pytest.raises(ValueError):
            AdapterType("invalid")


class TestAdapterFactory:
    """Test cases for AdapterFactory class."""

    def test_adapter_factory_initialization(self):
        """Test AdapterFactory initialization."""
        factory_instance = AdapterFactory()

        assert isinstance(factory_instance._adapters_cache, dict)
        assert len(factory_instance._adapters_cache) == 0

    def test_adapter_factory_get_adapters(self):
        """Test AdapterFactory _get_adapters method."""
        factory_instance = AdapterFactory()
        adapters = factory_instance._get_adapters()

        assert isinstance(adapters, dict)
        assert len(adapters) == 4
        assert AdapterType.AIOGRAM in adapters
        assert AdapterType.PYROGRAM in adapters
        assert AdapterType.TELETHON in adapters
        assert AdapterType.TELEBOT in adapters

    def test_adapter_factory_get_adapters_caching(self):
        """Test AdapterFactory _get_adapters caching."""
        factory_instance = AdapterFactory()

        adapters1 = factory_instance._get_adapters()
        assert len(adapters1) == 4
        assert len(factory_instance._adapters_cache) == 0

        adapters2 = factory_instance._get_adapters()
        assert len(adapters2) == 4
        assert adapters1 == adapters2

    def test_adapter_factory_create_adapter_aiogram(self):
        """Test AdapterFactory create_adapter for aiogram."""
        factory_instance = AdapterFactory()

        with patch(
            "ttskit.telegram.aiogram_adapter.AiogramAdapter"
        ) as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            result = factory_instance.create_adapter(AdapterType.AIOGRAM, "test_token")

            mock_adapter_class.assert_called_once_with("test_token")
            assert result == mock_adapter

    def test_adapter_factory_create_adapter_pyrogram(self):
        """Test AdapterFactory create_adapter for pyrogram."""
        factory_instance = AdapterFactory()

        with patch(
            "ttskit.telegram.pyrogram_adapter.PyrogramAdapter"
        ) as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            result = factory_instance.create_adapter(
                AdapterType.PYROGRAM, "test_token", api_id=12345, api_hash="test_hash"
            )

            mock_adapter_class.assert_called_once_with(
                "test_token", api_id=12345, api_hash="test_hash"
            )
            assert result == mock_adapter

    def test_adapter_factory_create_adapter_telethon(self):
        """Test AdapterFactory create_adapter for telethon."""
        factory_instance = AdapterFactory()

        with patch(
            "ttskit.telegram.telethon_adapter.TelethonAdapter"
        ) as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            result = factory_instance.create_adapter(
                AdapterType.TELETHON, "test_token", api_id=12345, api_hash="test_hash"
            )

            mock_adapter_class.assert_called_once_with(
                "test_token", api_id=12345, api_hash="test_hash"
            )
            assert result == mock_adapter

    def test_adapter_factory_create_adapter_telebot(self):
        """Test AdapterFactory create_adapter for telebot."""
        factory_instance = AdapterFactory()

        with patch(
            "ttskit.telegram.telebot_adapter.TelebotAdapter"
        ) as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter

            result = factory_instance.create_adapter(
                AdapterType.TELEBOT, "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
            )

            mock_adapter_class.assert_called_once_with(
                "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"
            )
            assert result == mock_adapter

    def test_adapter_factory_create_adapter_invalid_type(self):
        """Test AdapterFactory create_adapter with invalid type."""
        factory_instance = AdapterFactory()

        with pytest.raises(ValueError):
            factory_instance.create_adapter("invalid", "test_token")

    def test_adapter_factory_create_adapter_import_error(self):
        """Test AdapterFactory create_adapter with import error."""
        factory_instance = AdapterFactory()

        with patch(
            "ttskit.telegram.aiogram_adapter.AiogramAdapter",
            side_effect=ImportError("Module not found"),
        ):
            with pytest.raises(ImportError):
                factory_instance.create_adapter(AdapterType.AIOGRAM, "test_token")

    def test_adapter_factory_get_available_adapters(self):
        """Test AdapterFactory get_available_adapters method."""
        factory_instance = AdapterFactory()
        adapters = factory_instance.get_available_adapters()

        assert isinstance(adapters, list)
        assert len(adapters) == 4
        assert AdapterType.AIOGRAM in adapters
        assert AdapterType.PYROGRAM in adapters
        assert AdapterType.TELETHON in adapters
        assert AdapterType.TELEBOT in adapters

    def test_adapter_factory_get_adapter_info(self):
        """Test AdapterFactory get_adapter_info method."""
        factory_instance = AdapterFactory()

        info = factory_instance.get_adapter_info(AdapterType.AIOGRAM)

        assert isinstance(info, dict)
        assert info["type"] == "aiogram"
        assert info["class"] == "AiogramAdapter"
        assert info["module"] == "ttskit.telegram.aiogram_adapter"
        assert info["available"] is True
        assert "description" in info

    def test_adapter_factory_get_adapter_info_invalid(self):
        """Test AdapterFactory get_adapter_info with invalid type."""
        factory_instance = AdapterFactory()

        info = factory_instance.get_adapter_info("invalid")

        assert info is None

    def test_adapter_factory_get_all_adapters_info(self):
        """Test AdapterFactory get_all_adapters_info method."""
        factory_instance = AdapterFactory()

        all_info = factory_instance.get_all_adapters_info()

        assert isinstance(all_info, dict)
        assert len(all_info) == 4
        assert "aiogram" in all_info
        assert "pyrogram" in all_info
        assert "telethon" in all_info
        assert "telebot" in all_info

        for adapter_type, info in all_info.items():
            assert isinstance(info, dict)
            assert "type" in info
            assert "class" in info
            assert "module" in info
            assert "available" in info

    def test_adapter_factory_register_adapter(self):
        """Test AdapterFactory register_adapter method."""
        factory_instance = AdapterFactory()

        class CustomAdapter:
            def __init__(self, bot_token):
                self.bot_token = bot_token

        factory_instance.register_adapter(AdapterType.AIOGRAM, CustomAdapter)

        adapters = factory_instance._get_adapters()
        assert adapters[AdapterType.AIOGRAM] == CustomAdapter

    def test_adapter_factory_unregister_adapter(self):
        """Test AdapterFactory unregister_adapter method."""
        factory_instance = AdapterFactory()

        class CustomAdapter:
            def __init__(self, bot_token):
                self.bot_token = bot_token

        factory_instance.register_adapter(AdapterType.AIOGRAM, CustomAdapter)

        initial_adapters = factory_instance._get_adapters()
        assert AdapterType.AIOGRAM in initial_adapters
        assert initial_adapters[AdapterType.AIOGRAM] == CustomAdapter

        factory_instance.unregister_adapter(AdapterType.AIOGRAM)

        adapters = factory_instance._get_adapters()
        assert AdapterType.AIOGRAM in adapters
        assert adapters[AdapterType.AIOGRAM] != CustomAdapter

    def test_adapter_factory_unregister_nonexistent_adapter(self):
        """Test AdapterFactory unregister_adapter with nonexistent adapter."""
        factory_instance = AdapterFactory()

        factory_instance.unregister_adapter("nonexistent")

    def test_adapter_factory_check_dependencies_aiogram(self):
        """Test AdapterFactory check_dependencies for aiogram."""
        factory_instance = AdapterFactory()

        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = Mock()

            deps = factory_instance.check_dependencies(AdapterType.AIOGRAM)

            assert deps["available"] is True

    def test_adapter_factory_check_dependencies_aiogram_unavailable(self):
        """Test AdapterFactory check_dependencies for aiogram when unavailable."""
        factory_instance = AdapterFactory()

        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = None

            deps = factory_instance.check_dependencies(AdapterType.AIOGRAM)

            assert deps["available"] is False

    def test_adapter_factory_check_dependencies_pyrogram(self):
        """Test AdapterFactory check_dependencies for pyrogram."""
        factory_instance = AdapterFactory()

        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = Mock()

            deps = factory_instance.check_dependencies(AdapterType.PYROGRAM)

            assert deps["available"] is True

    def test_adapter_factory_check_dependencies_telethon(self):
        """Test AdapterFactory check_dependencies for telethon."""
        factory_instance = AdapterFactory()

        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = Mock()

            deps = factory_instance.check_dependencies(AdapterType.TELETHON)

            assert deps["available"] is True

    def test_adapter_factory_check_dependencies_telebot(self):
        """Test AdapterFactory check_dependencies for telebot."""
        factory_instance = AdapterFactory()

        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_find_spec.return_value = Mock()

            deps = factory_instance.check_dependencies(AdapterType.TELEBOT)

            assert deps["available"] is True

    def test_adapter_factory_check_dependencies_invalid(self):
        """Test AdapterFactory check_dependencies with invalid type."""
        factory_instance = AdapterFactory()

        deps = factory_instance.check_dependencies("invalid")

        assert deps["available"] is False
        assert "error" in deps
        assert "not supported" in deps["error"]

    def test_adapter_factory_check_dependencies_exception(self):
        """Test AdapterFactory check_dependencies with exception."""
        factory_instance = AdapterFactory()

        with patch("importlib.util.find_spec", side_effect=Exception("Test error")):
            deps = factory_instance.check_dependencies(AdapterType.AIOGRAM)

            assert deps["available"] is False
            assert "error" in deps
            assert deps["error"] == "Test error"

    def test_adapter_factory_get_recommended_adapter(self):
        """Test AdapterFactory get_recommended_adapter method."""
        factory_instance = AdapterFactory()

        with patch.object(factory_instance, "check_dependencies") as mock_check:
            mock_check.return_value = {"available": True}

            recommended = factory_instance.get_recommended_adapter()

            assert recommended == AdapterType.AIOGRAM

    def test_adapter_factory_get_recommended_adapter_none_available(self):
        """Test AdapterFactory get_recommended_adapter when none available."""
        factory_instance = AdapterFactory()

        with patch.object(factory_instance, "check_dependencies") as mock_check:
            mock_check.return_value = {"available": False}

            recommended = factory_instance.get_recommended_adapter()

            assert recommended is None

    def test_adapter_factory_get_adapters_by_dependencies(self):
        """Test AdapterFactory get_adapters_by_dependencies method."""
        factory_instance = AdapterFactory()

        with patch.object(factory_instance, "check_dependencies") as mock_check:

            def mock_check_side_effect(adapter_type):
                if adapter_type == AdapterType.AIOGRAM:
                    return {"available": True}
                else:
                    return {"available": False}

            mock_check.side_effect = mock_check_side_effect

            result = factory_instance.get_adapters_by_dependencies()

            assert isinstance(result, dict)
            assert "available" in result
            assert "unavailable" in result
            assert AdapterType.AIOGRAM in result["available"]
            assert AdapterType.PYROGRAM in result["unavailable"]
            assert AdapterType.TELETHON in result["unavailable"]
            assert AdapterType.TELEBOT in result["unavailable"]

    def test_adapter_factory_adapter_type_property(self):
        """Test AdapterFactory AdapterType property."""
        factory_instance = AdapterFactory()

        assert factory_instance.AdapterType == AdapterType


class TestGlobalFunctions:
    """Test cases for global factory functions."""

    def test_create_adapter_valid_type(self):
        """Test create_adapter function with valid type."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_adapter = Mock()
            mock_factory.create_adapter.return_value = mock_adapter

            result = create_adapter("aiogram", "test_token")

            mock_factory.create_adapter.assert_called_once_with(
                AdapterType.AIOGRAM, "test_token"
            )
            assert result == mock_adapter

    def test_create_adapter_with_kwargs(self):
        """Test create_adapter function with additional kwargs."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_adapter = Mock()
            mock_factory.create_adapter.return_value = mock_adapter

            result = create_adapter(
                "pyrogram", "test_token", api_id=12345, api_hash="test_hash"
            )

            mock_factory.create_adapter.assert_called_once_with(
                AdapterType.PYROGRAM, "test_token", api_id=12345, api_hash="test_hash"
            )
            assert result == mock_adapter

    def test_create_adapter_invalid_type(self):
        """Test create_adapter function with invalid type."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_factory.get_available_adapters.return_value = [
                AdapterType.AIOGRAM,
                AdapterType.PYROGRAM,
            ]

            with pytest.raises(ValueError, match="Unknown adapter type: invalid"):
                create_adapter("invalid", "test_token")

    def test_get_available_adapters(self):
        """Test get_available_adapters function."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_factory.get_available_adapters.return_value = [
                AdapterType.AIOGRAM,
                AdapterType.PYROGRAM,
            ]

            result = get_available_adapters()

            assert result == ["aiogram", "pyrogram"]

    def test_get_recommended_adapter(self):
        """Test get_recommended_adapter function."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_factory.get_recommended_adapter.return_value = AdapterType.AIOGRAM

            result = get_recommended_adapter()

            assert result == "aiogram"

    def test_get_recommended_adapter_none(self):
        """Test get_recommended_adapter function when none available."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_factory.get_recommended_adapter.return_value = None

            result = get_recommended_adapter()

            assert result is None

    def test_check_dependencies_valid_type(self):
        """Test check_dependencies function with valid type."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_factory.check_dependencies.return_value = {"available": True}

            result = check_dependencies("aiogram")

            mock_factory.check_dependencies.assert_called_once_with(AdapterType.AIOGRAM)
            assert result == {"available": True}

    def test_check_dependencies_invalid_type(self):
        """Test check_dependencies function with invalid type."""
        result = check_dependencies("invalid")

        assert result["available"] is False
        assert "error" in result
        assert "Unknown adapter type: invalid" in result["error"]

    def test_check_dependencies_case_insensitive(self):
        """Test check_dependencies function with case insensitive input."""
        with patch("ttskit.telegram.factory.factory") as mock_factory:
            mock_factory.check_dependencies.return_value = {"available": True}

            result = check_dependencies("AIOGRAM")

            mock_factory.check_dependencies.assert_called_once_with(AdapterType.AIOGRAM)
            assert result == {"available": True}


class TestGlobalFactoryInstance:
    """Test cases for global factory instance."""

    def test_global_factory_instance(self):
        """Test global factory instance."""
        assert isinstance(factory, AdapterFactory)
        assert factory is not None

    def test_global_factory_singleton_behavior(self):
        """Test that global factory behaves as singleton."""
        from ttskit.telegram.factory import factory as factory1
        from ttskit.telegram.factory import factory as factory2

        assert factory1 is factory2

    def test_global_factory_operations(self):
        """Test operations on global factory instance."""
        adapters = factory.get_available_adapters()
        assert isinstance(adapters, list)
        assert len(adapters) == 4

        info = factory.get_adapter_info(AdapterType.AIOGRAM)
        assert isinstance(info, dict)
        assert info["type"] == "aiogram"

        deps = factory.check_dependencies(AdapterType.AIOGRAM)
        assert isinstance(deps, dict)
        assert "available" in deps


class TestTelegramAdapterFactoryAlias:
    """Test cases for TelegramAdapterFactory alias."""

    def test_telegram_adapter_factory_alias(self):
        """Test TelegramAdapterFactory alias."""
        assert TelegramAdapterFactory == AdapterFactory

        factory_instance = TelegramAdapterFactory()
        assert isinstance(factory_instance, AdapterFactory)


class TestFactoryIntegration:
    """Integration tests for factory module."""

    def test_factory_end_to_end_workflow(self):
        """Test complete factory workflow."""
        factory_instance = AdapterFactory()

        adapters = factory_instance.get_available_adapters()
        assert len(adapters) == 4

        for adapter_type in adapters:
            info = factory_instance.get_adapter_info(adapter_type)
            assert info is not None
            assert info["available"] is True

        for adapter_type in adapters:
            deps = factory_instance.check_dependencies(adapter_type)
            assert isinstance(deps, dict)
            assert "available" in deps

        recommended = factory_instance.get_recommended_adapter()
        assert recommended is None or recommended in adapters

        by_deps = factory_instance.get_adapters_by_dependencies()
        assert isinstance(by_deps, dict)
        assert "available" in by_deps
        assert "unavailable" in by_deps

    def test_factory_error_handling(self):
        """Test factory error handling."""
        factory_instance = AdapterFactory()

        with pytest.raises(ValueError):
            factory_instance.create_adapter("invalid", "test_token")

        info = factory_instance.get_adapter_info("invalid")
        assert info is None

        deps = factory_instance.check_dependencies("invalid")
        assert deps["available"] is False
        assert "error" in deps

    def test_factory_custom_adapter_registration(self):
        """Test custom adapter registration workflow."""
        factory_instance = AdapterFactory()

        class CustomAdapter:
            def __init__(self, bot_token):
                self.bot_token = bot_token

        factory_instance.register_adapter(AdapterType.AIOGRAM, CustomAdapter)

        adapters = factory_instance._get_adapters()
        assert adapters[AdapterType.AIOGRAM] == CustomAdapter

        adapter = factory_instance.create_adapter(AdapterType.AIOGRAM, "test_token")
        assert isinstance(adapter, CustomAdapter)
        assert adapter.bot_token == "test_token"

        factory_instance.unregister_adapter(AdapterType.AIOGRAM)

        adapters = factory_instance._get_adapters()
        assert AdapterType.AIOGRAM in adapters
        assert adapters[AdapterType.AIOGRAM] != CustomAdapter
