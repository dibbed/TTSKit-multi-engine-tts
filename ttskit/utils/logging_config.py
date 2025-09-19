"""Centralized logging configuration for TTSKit.

This module sets up the root logger with a standard format and level,
ensuring consistent logging across the application. Provides helpers
for configuration and named loggers.
"""

import logging


def setup_logging(level: str | None = None) -> None:
    """Configure the root logger with a standard format and level.

    Sets up basicConfig if no handlers exist; otherwise updates level.
    Ensures logging is initialized only once.

    Args:
        level: Logging level as string (e.g., 'INFO', 'DEBUG'); defaults to INFO if None.

    Notes:
        Format includes filename, line number, and function name for better debugging.
        Converts level to numeric via getattr; falls back to INFO.
        Checks logging.getLogger().handlers to avoid re-configuring.
    """
    if level:
        numeric = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric = logging.INFO

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=numeric,
            format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d:%(funcName)s() - %(message)s",
        )
    else:
        logging.getLogger().setLevel(numeric)


def get_logger(name: str | None = None) -> logging.Logger:
    """Retrieve a named logger instance, ensuring setup_logging is called.

    Uses the module name (__name__) if name is None for hierarchical logging.

    Args:
        name: Logger name (str or None); defaults to caller's __name__.

    Returns:
        logging.Logger: Configured instance ready for use.
    """
    setup_logging()
    return logging.getLogger(name)
