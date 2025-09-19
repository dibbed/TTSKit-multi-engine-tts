"""
FastAPI application module providing TTSKit's core API components.

This module provides the FastAPI application and related components
for the TTSKit REST API service.
"""

from .app import app, create_app

__all__ = ["app", "create_app"]
