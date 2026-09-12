"""Process lifecycle manager for TTSKit.

Provides supervised process restart and shutdown management, shutdown hooks,
and supervisor detection (systemd, docker, supervisor, Kubernetes, or explicit env).
"""

import asyncio
import os
import sys
from collections.abc import Callable, Coroutine
from enum import StrEnum
from typing import Any

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class LifecycleMode(StrEnum):
    SUPERVISED = "supervised"
    STANDALONE = "standalone"


class ProcessLifecycleManager:
    """Manages process lifecycle, graceful shutdown hooks, and supervised restart."""

    def __init__(self, exit_handler: Callable[[int], Any] | None = None) -> None:
        self._hooks: list[Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]] = []
        self._exit_handler = exit_handler

    def register_shutdown_hook(
        self, hook: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    ) -> None:
        """Register a hook to execute prior to shutdown or restart."""
        if hook not in self._hooks:
            self._hooks.append(hook)

    def unregister_shutdown_hook(
        self, hook: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    ) -> None:
        """Unregister a previously registered hook."""
        if hook in self._hooks:
            self._hooks.remove(hook)

    def detect_mode(self) -> LifecycleMode:
        """Detect whether the process runs under a process supervisor."""
        env = os.environ
        if env.get("TTSKIT_SUPERVISED", "").lower() in ("1", "true", "yes"):
            return LifecycleMode.SUPERVISED
        if env.get("SUPERVISED_MODE", "").lower() in ("1", "true", "yes"):
            return LifecycleMode.SUPERVISED
        if "INVOCATION_ID" in env or "JOURNAL_STREAM" in env:
            return LifecycleMode.SUPERVISED
        if "SUPERVISOR_ENABLED" in env:
            return LifecycleMode.SUPERVISED
        if "KUBERNETES_SERVICE_HOST" in env:
            return LifecycleMode.SUPERVISED
        if os.path.exists("/.dockerenv"):
            return LifecycleMode.SUPERVISED
        return LifecycleMode.STANDALONE

    def is_restart_supported(self) -> bool:
        """Check if restart is supported in the current environment."""
        return self.detect_mode() == LifecycleMode.SUPERVISED

    async def run_shutdown_hooks(self) -> None:
        """Execute all registered shutdown hooks safely."""
        for hook in list(self._hooks):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    res = hook()
                    if asyncio.iscoroutine(res):
                        await res
            except Exception as e:
                logger.warning(f"Error executing shutdown hook {hook}: {e}")

    async def request_restart(
        self,
        grace_period_seconds: float = 0.5,
        use_execv_fallback: bool = False,
    ) -> dict[str, Any]:
        """Request a process restart.

        Under a supervisor, shuts down gracefully with exit code 0 to allow supervisor restart.
        In standalone mode without an external supervisor, returns unsupported status
        unless explicit execv fallback is enabled.
        """
        mode = self.detect_mode()
        logger.info(f"Process restart requested in mode: {mode}")

        await self.run_shutdown_hooks()

        if mode == LifecycleMode.SUPERVISED:
            if self._exit_handler:
                self._exit_handler(0)
            else:
                try:
                    asyncio.create_task(self._delayed_exit(grace_period_seconds, 0))
                except RuntimeError:
                    pass
            return {
                "supported": True,
                "mode": mode.value,
                "message": "Restart initiated via process supervisor",
            }

        if use_execv_fallback and hasattr(os, "execv"):
            if self._exit_handler:
                self._exit_handler(0)
            else:
                try:
                    asyncio.create_task(self._delayed_execv(grace_period_seconds))
                except RuntimeError:
                    pass
            return {
                "supported": True,
                "mode": mode.value,
                "message": "Restart initiated via process re-execution",
            }

        return {
            "supported": False,
            "mode": mode.value,
            "message": "Restart is unavailable without a process supervisor",
        }

    async def request_shutdown(self, grace_period_seconds: float = 0.5) -> dict[str, Any]:
        """Request a clean process shutdown."""
        logger.info("Process shutdown requested")
        await self.run_shutdown_hooks()

        if self._exit_handler:
            self._exit_handler(0)
        else:
            try:
                asyncio.create_task(self._delayed_exit(grace_period_seconds, 0))
            except RuntimeError:
                pass

        return {
            "supported": True,
            "message": "Shutdown initiated",
        }

    async def _delayed_exit(self, delay: float, code: int = 0) -> None:
        try:
            await asyncio.sleep(delay)
        except Exception:
            pass
        os._exit(code)

    async def _delayed_execv(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            os.execv(sys.executable, [sys.executable] + sys.argv)  # noqa: S606
        except Exception as e:
            logger.error(f"Failed to execv restart: {e}")
            os._exit(1)


lifecycle_manager = ProcessLifecycleManager()
