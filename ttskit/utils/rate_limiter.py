"""Rate limiting utilities for TTSKit."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from ..config import settings
from ..exceptions import RateLimitExceededError

try:
    import redis  # type: ignore

    _REDIS_AVAILABLE = True
except Exception:
    redis = None  # type: ignore
    _REDIS_AVAILABLE = False


@dataclass
class RateLimitInfo:
    """Rate limit information for a user."""

    requests: int
    window_start: float
    blocked_until: float | None = None


class RateLimiter:
    """Rate limiter for per-user request limiting."""

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: int | None = None,
        block_duration: int = 60,
    ):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            block_duration: Duration to block user after limit exceeded
        """
        self.max_requests = max_requests or settings.rate_limit_rpm
        self.window_seconds = window_seconds or settings.rate_limit_window
        self.block_duration = block_duration

        # Store rate limit info per user
        self._user_limits: dict[str, RateLimitInfo] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, user_id: str) -> tuple[bool, str]:
        """Check if user is allowed to make a request.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (is_allowed, message)
        """
        async with self._lock:
            current_time = time.time()

            # Get or create user limit info
            if user_id not in self._user_limits:
                self._user_limits[user_id] = RateLimitInfo(
                    requests=0, window_start=current_time
                )

            user_limit = self._user_limits[user_id]

            # Check if user is blocked
            if user_limit.blocked_until and current_time < user_limit.blocked_until:
                remaining = int(user_limit.blocked_until - current_time)
                return False, f"Rate limit exceeded. Try again in {remaining} seconds."

            # Check if window has expired
            if current_time - user_limit.window_start >= self.window_seconds:
                # Reset window
                user_limit.requests = 0
                user_limit.window_start = current_time
                user_limit.blocked_until = None

            # Check if limit exceeded
            if user_limit.requests >= self.max_requests:
                # Block user
                user_limit.blocked_until = current_time + self.block_duration
                return (
                    False,
                    f"Rate limit exceeded. Blocked for {self.block_duration} seconds.",
                )

            # Allow request
            user_limit.requests += 1
            remaining = self.max_requests - user_limit.requests
            return (
                True,
                f"Request allowed. {remaining} requests remaining in this window.",
            )

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        """Get rate limit statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with user statistics
        """
        async with self._lock:
            current_time = time.time()

            if user_id not in self._user_limits:
                return {
                    "requests": 0,
                    "remaining": self.max_requests,
                    "window_start": current_time,
                    "window_remaining": self.window_seconds,
                    "blocked": False,
                    "blocked_until": None,
                }

            user_limit = self._user_limits[user_id]

            # Check if window has expired
            if current_time - user_limit.window_start >= self.window_seconds:
                return {
                    "requests": 0,
                    "remaining": self.max_requests,
                    "window_start": current_time,
                    "window_remaining": self.window_seconds,
                    "blocked": False,
                    "blocked_until": None,
                }

            window_remaining = max(
                0, self.window_seconds - (current_time - user_limit.window_start)
            )
            remaining = max(0, self.max_requests - user_limit.requests)
            blocked = bool(
                user_limit.blocked_until and current_time < user_limit.blocked_until
            )

            return {
                "requests": user_limit.requests,
                "remaining": remaining,
                "window_start": user_limit.window_start,
                "window_remaining": window_remaining,
                "blocked": blocked,
                "blocked_until": user_limit.blocked_until,
            }

    async def reset_user(self, user_id: str) -> None:
        """Reset rate limit for a user.

        Args:
            user_id: User identifier
        """
        async with self._lock:
            if user_id in self._user_limits:
                del self._user_limits[user_id]

    async def get_global_stats(self) -> dict[str, Any]:
        """Get global rate limiter statistics.

        Returns:
            Dictionary with global statistics
        """
        async with self._lock:
            current_time = time.time()

            # Clean up expired entries
            expired_users = []
            for user_id, user_limit in self._user_limits.items():
                if current_time - user_limit.window_start >= self.window_seconds and (
                    not user_limit.blocked_until
                    or current_time >= user_limit.blocked_until
                ):
                    expired_users.append(user_id)

            for user_id in expired_users:
                del self._user_limits[user_id]

            # Calculate statistics
            total_users = len(self._user_limits)
            blocked_users = sum(
                1
                for ul in self._user_limits.values()
                if ul.blocked_until and current_time < ul.blocked_until
            )
            active_users = total_users - blocked_users

            return {
                "total_users": total_users,
                "active_users": active_users,
                "blocked_users": blocked_users,
                "max_requests_per_window": self.max_requests,
                "window_seconds": self.window_seconds,
                "block_duration": self.block_duration,
            }

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get rate limit information for a user."""
        try:
            is_allowed, message = await self.is_allowed(user_id)
            stats = await self.get_user_stats(user_id)
            return {
                "user_id": user_id,
                "rate_limited": not is_allowed,
                "message": message,
                "remaining_requests": stats.get("remaining", 0),
                "reset_time": stats.get("blocked_until"),
            }
        except Exception as e:
            return {
                "user_id": user_id,
                "error": str(e),
                "rate_limited": False,
                "remaining_requests": 0,
                "reset_time": None,
            }


class RedisRateLimiter:
    """Redis-backed rate limiter (best-effort, single-node)."""

    def __init__(
        self,
        redis_url: str,
        max_requests: int | None = None,
        window_seconds: int | None = None,
        block_duration: int = 60,
    ) -> None:
        self.max_requests = max_requests or settings.rate_limit_rpm
        self.window_seconds = window_seconds or settings.rate_limit_window
        self.block_duration = block_duration
        self._redis = redis.from_url(redis_url, decode_responses=True)  # type: ignore[arg-type]

    def _keys(self, user_id: str) -> tuple[str, str]:
        return f"rl:c:{user_id}", f"rl:b:{user_id}"

    async def is_allowed(self, user_id: str) -> tuple[bool, str]:
        count_key, block_key = self._keys(user_id)

        def _op() -> tuple[bool, str]:
            # Blocked?
            if self._redis.exists(block_key):
                ttl = self._redis.ttl(block_key)
                ttl = int(ttl) if ttl and ttl > 0 else self.block_duration
                return False, f"Rate limit exceeded. Try again in {ttl} seconds."

            pipe = self._redis.pipeline()
            pipe.incr(count_key)
            pipe.expire(count_key, self.window_seconds)
            cnt, _ = pipe.execute()
            cnt = int(cnt)
            if cnt > self.max_requests:
                # Set block and reset counter window
                self._redis.setex(block_key, self.block_duration, "1")
                return (
                    False,
                    f"Rate limit exceeded. Blocked for {self.block_duration} seconds.",
                )
            remaining = max(0, self.max_requests - cnt)
            return (
                True,
                f"Request allowed. {remaining} requests remaining in this window.",
            )

        return await asyncio.to_thread(_op)

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        count_key, block_key = self._keys(user_id)

        def _op() -> dict[str, Any]:
            cnt = self._redis.get(count_key)
            cnt = int(cnt) if cnt else 0
            ttl = self._redis.ttl(count_key)
            ttl = int(ttl) if ttl and ttl > 0 else self.window_seconds
            blocked = self._redis.exists(block_key) == 1
            blocked_ttl = self._redis.ttl(block_key) if blocked else -1
            remaining = max(0, self.max_requests - cnt)
            return {
                "requests": cnt,
                "remaining": remaining,
                "window_start": None,
                "window_remaining": ttl,
                "blocked": blocked,
                "blocked_until": int(time.time()) + int(blocked_ttl)
                if blocked_ttl and blocked_ttl > 0
                else None,
            }

        return await asyncio.to_thread(_op)

    async def reset_user(self, user_id: str) -> None:
        count_key, block_key = self._keys(user_id)

        def _op() -> None:
            self._redis.delete(count_key)
            self._redis.delete(block_key)

        await asyncio.to_thread(_op)

    async def get_global_stats(self) -> dict[str, Any]:
        # Not efficient to scan; return configured limits only
        return {
            "total_users": None,
            "active_users": None,
            "blocked_users": None,
            "max_requests_per_window": self.max_requests,
            "window_seconds": self.window_seconds,
            "block_duration": self.block_duration,
        }

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get rate limit information for a user."""
        try:
            is_allowed, message = await self.is_allowed(user_id)
            stats = await self.get_user_stats(user_id)
            return {
                "user_id": user_id,
                "rate_limited": not is_allowed,
                "message": message,
                "remaining_requests": stats.get("remaining", 0),
                "reset_time": stats.get("blocked_until"),
            }
        except Exception as e:
            return {
                "user_id": user_id,
                "error": str(e),
                "rate_limited": False,
                "remaining_requests": 0,
                "reset_time": None,
            }


def _create_rate_limiter() -> object:
    if settings.enable_rate_limiting and settings.redis_url and _REDIS_AVAILABLE:
        try:
            return RedisRateLimiter(
                redis_url=settings.redis_url,
                max_requests=settings.rate_limit_rpm,
                window_seconds=settings.rate_limit_window,
                block_duration=60,
            )
        except Exception as err:
            # Log and gracefully fall back to in-memory limiter
            import logging

            logging.getLogger(__name__).warning(
                "RedisRateLimiter initialization failed, falling back to in-memory: %s",
                err,
            )
    return RateLimiter()


# Global rate limiter instance
rate_limiter = _create_rate_limiter()


async def check_rate_limit(user_id: str) -> tuple[bool, str]:
    """Check rate limit for a user.

    Args:
        user_id: User identifier

    Returns:
        Tuple of (is_allowed, message)
    """
    return await rate_limiter.is_allowed(user_id)


async def get_rate_limit_stats(user_id: str) -> dict[str, Any]:
    """Get rate limit statistics for a user.

    Args:
        user_id: User identifier

    Returns:
        Dictionary with user statistics
    """
    return await rate_limiter.get_user_stats(user_id)


async def reset_rate_limit(user_id: str) -> None:
    """Reset rate limit for a user.

    Args:
        user_id: User identifier
    """
    await rate_limiter.reset_user(user_id)


async def get_global_rate_limit_stats() -> dict[str, Any]:
    """Get global rate limiter statistics.

    Returns:
        Dictionary with global statistics
    """
    return await rate_limiter.get_global_stats()


# Import from exceptions module to avoid duplication


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_rate_limiter():
    """Get the global rate limiter instance."""
    return rate_limiter


async def is_rate_limited(user_id: str) -> bool:
    """Check if user is rate limited."""
    is_allowed, _ = await check_rate_limit(user_id)
    return not is_allowed


async def get_user_info(user_id: str) -> dict[str, Any]:
    """Get rate limit information for a user."""
    try:
        is_allowed, remaining = await check_rate_limit(user_id)
        return {
            "user_id": user_id,
            "rate_limited": not is_allowed,
            "remaining_requests": remaining,
            "reset_time": None,  # Could be implemented with Redis TTL
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "error": str(e),
            "rate_limited": False,
            "remaining_requests": 0,
            "reset_time": None,
        }


async def get_global_stats() -> dict[str, Any]:
    """Get global rate limiter statistics."""
    try:
        return await rate_limiter.get_global_stats()
    except Exception as e:
        return {"error": str(e)}


# Export RateLimitExceededError for external use
__all__ = [
    "RateLimiter",
    "RateLimitExceededError",
    "get_rate_limiter",
    "is_rate_limited",
    "check_rate_limit",
    "get_global_stats",
    "get_user_info",
]
