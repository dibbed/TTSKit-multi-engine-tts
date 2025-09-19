"""API routers module."""

from .admin import router as admin_router
from .engines import router as engines_router
from .synthesis import router as synthesis_router
from .system import router as system_router

__all__ = ["admin_router", "engines_router", "synthesis_router", "system_router"]
