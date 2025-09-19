"""Compatibility factory module.

This module forwards factory APIs to `ttskit.telegram.factory` so
imports like `ttskit.adapters.factory` work for both runtime and type checkers.
"""

from ..telegram.factory import *  # noqa: F401,F403
