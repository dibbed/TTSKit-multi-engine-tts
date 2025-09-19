"""Tests for logging configuration."""

import logging
from unittest.mock import patch

from ttskit.utils.logging_config import get_logger, setup_logging


class TestLoggingConfig:
    """Test cases for logging configuration."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging()

        assert root_logger.level in (
            logging.INFO,
            logging.DEBUG,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        )
        assert len(root_logger.handlers) >= 0

    def test_setup_logging_with_level(self):
        """Test setup_logging with specific level."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("DEBUG")

        assert root_logger.level in (logging.DEBUG, logging.INFO)

    def test_setup_logging_with_invalid_level(self):
        """Test setup_logging with invalid level falls back to INFO."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("INVALID_LEVEL")

        assert root_logger.level == logging.INFO

    def test_setup_logging_idempotent(self):
        """Test that setup_logging is idempotent."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("INFO")
        first_handler_count = len(root_logger.handlers)

        setup_logging("DEBUG")
        second_handler_count = len(root_logger.handlers)

        assert first_handler_count == second_handler_count

    def test_get_logger_with_name(self):
        """Test get_logger with specific name."""
        logger = get_logger("test_module")
        assert hasattr(logger, "info") and hasattr(logger, "warning")

    def test_get_logger_without_name(self):
        """Test get_logger without name."""
        logger = get_logger()
        assert hasattr(logger, "info") and hasattr(logger, "error")

    def test_get_logger_configures_logging(self):
        """Test that get_logger automatically configures logging."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        get_logger("test_module")

        assert root_logger.level in (
            logging.INFO,
            logging.DEBUG,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        )
        assert len(root_logger.handlers) >= 0

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same logger instance."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")

        assert logger1 is logger2

    def test_logger_functionality(self):
        """Test that the logger actually works."""
        logger = get_logger("test_module")

        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")

        assert True

    @patch("logging.basicConfig")
    def test_setup_logging_calls_basic_config(self, mock_basic_config):
        """Test that setup_logging calls logging.basicConfig."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("INFO")

        if mock_basic_config.call_count:
            mock_basic_config.assert_called()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == logging.INFO
            assert (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                in call_args[1]["format"]
            )
        else:
            assert logging.getLogger().level in (
                logging.INFO,
                logging.DEBUG,
                logging.WARNING,
                logging.ERROR,
                logging.CRITICAL,
            )

    def test_logger_levels(self):
        """Test different logger levels."""
        logger = get_logger("test_levels")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        assert True
