"""Tests for rate limiter utilities."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ttskit.utils.rate_limiter import (
    RateLimiter,
    RateLimitExceededError,
    RedisRateLimiter,
    _create_rate_limiter,
    check_rate_limit,
    get_global_rate_limit_stats,
    get_global_stats,
    get_rate_limit_stats,
    get_rate_limiter,
    get_user_info,
    is_rate_limited,
    reset_rate_limit,
)


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60
        assert limiter.block_duration == 60

    def test_initialization_default_values(self):
        """Test RateLimiter initialization with default values."""
        with patch("ttskit.utils.rate_limiter.settings") as mock_settings:
            mock_settings.rate_limit_rpm = 5
            mock_settings.rate_limit_window = 60

            limiter = RateLimiter()
            assert limiter.max_requests == 5
            assert limiter.window_seconds == 60
            assert limiter.block_duration == 60

    @pytest.mark.asyncio
    async def test_is_allowed_first_request(self):
        """Test is_allowed when user makes first request."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        is_allowed, message = await limiter.is_allowed("user1")

        assert is_allowed is True
        assert "4 requests remaining" in message

    @pytest.mark.asyncio
    async def test_is_allowed_exceeds_limit(self):
        """Test is_allowed when user exceeds limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        is_allowed, message = await limiter.is_allowed("user1")

        assert is_allowed is False
        assert "Rate limit exceeded" in message

    @pytest.mark.asyncio
    async def test_get_user_stats(self):
        """Test get_user_stats method."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        stats = await limiter.get_user_stats("user1")

        assert stats["requests"] == 2
        assert stats["remaining"] == 3
        assert stats["blocked"] is False

    @pytest.mark.asyncio
    async def test_get_global_stats(self):
        """Test get_global_stats method."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user2")

        stats = await limiter.get_global_stats()

        assert stats["total_users"] == 2
        assert stats["active_users"] == 2
        assert stats["blocked_users"] == 0

    @pytest.mark.asyncio
    async def test_reset_user(self):
        """Test reset_user method."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        await limiter.reset_user("user1")

        is_allowed, _ = await limiter.is_allowed("user1")

        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test get_user_info method."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        info = await limiter.get_user_info("user1")

        assert info["user_id"] == "user1"
        assert info["rate_limited"] is False


class TestRateLimitExceededError:
    """Test RateLimitExceededError exception."""

    def test_creation(self):
        """Test creating RateLimitExceededError."""
        error = RateLimitExceededError("user123", 5, 60)
        assert error.user_id == "user123"
        assert error.max_requests == 5
        assert error.window_seconds == 60
        assert str(error) == "Rate limit exceeded for user user123"

    def test_inheritance(self):
        """Test RateLimitExceededError inheritance."""
        error = RateLimitExceededError("user123", 5, 60)
        assert isinstance(error, Exception)


class TestRateLimiterFunctions:
    """Test rate limiter functions."""

    def test_get_rate_limiter(self):
        """Test get_rate_limiter function."""
        limiter = get_rate_limiter()
        assert hasattr(limiter, "is_allowed")
        assert hasattr(limiter, "get_user_stats")

    @pytest.mark.asyncio
    async def test_is_rate_limited(self):
        """Test is_rate_limited function."""
        with patch("ttskit.utils.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (False, "Rate limit exceeded")

            result = await is_rate_limited("user123")

            assert result is True
            mock_check.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_check_rate_limit(self):
        """Test check_rate_limit function."""
        with patch("ttskit.utils.rate_limiter.rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(True, "Request allowed"))

            result = await check_rate_limit("user123")

            assert result == (True, "Request allowed")
            mock_limiter.is_allowed.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_global_stats(self):
        """Test get_global_stats function."""
        with patch("ttskit.utils.rate_limiter.rate_limiter") as mock_limiter:
            mock_limiter.get_global_stats = AsyncMock(return_value={"total_users": 10})

            result = await get_global_stats()

            assert result == {"total_users": 10}
            mock_limiter.get_global_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test get_user_info function."""
        with patch("ttskit.utils.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, "Request allowed")

            result = await get_user_info("user123")

            assert result["user_id"] == "user123"
            assert result["rate_limited"] is False
            mock_check.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_user_info_with_error(self):
        """Test get_user_info function with error."""
        with patch(
            "ttskit.utils.rate_limiter.check_rate_limit",
            side_effect=Exception("Rate limit error"),
        ):
            result = await get_user_info("user123")

            assert result["user_id"] == "user123"
            assert result["error"] == "Rate limit error"
            assert result["rate_limited"] is False


class TestRedisRateLimiter:
    """Test RedisRateLimiter class."""

    def test_initialization(self):
        """Test RedisRateLimiter initialization."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis.from_url.return_value = MagicMock()

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379",
                max_requests=10,
                window_seconds=60,
                block_duration=120,
            )

            assert limiter.max_requests == 10
            assert limiter.window_seconds == 60
            assert limiter.block_duration == 120
            mock_redis.from_url.assert_called_once_with(
                "redis://localhost:6379", decode_responses=True
            )

    def test_initialization_default_values(self):
        """Test RedisRateLimiter initialization with default values."""
        with (
            patch("ttskit.utils.rate_limiter.redis") as mock_redis,
            patch("ttskit.utils.rate_limiter.settings") as mock_settings,
        ):
            mock_redis.from_url.return_value = MagicMock()
            mock_settings.rate_limit_rpm = 5
            mock_settings.rate_limit_window = 60

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")

            assert limiter.max_requests == 5
            assert limiter.window_seconds == 60
            assert limiter.block_duration == 60

    def test_keys_method(self):
        """Test _keys method."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis.from_url.return_value = MagicMock()

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
            count_key, block_key = limiter._keys("user123")

            assert count_key == "rl:c:user123"
            assert block_key == "rl:b:user123"

    @pytest.mark.asyncio
    async def test_is_allowed_blocked_user(self):
        """Test is_allowed when user is blocked."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.return_value = True
            mock_redis_client.ttl.return_value = 30

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
            is_allowed, message = await limiter.is_allowed("user123")

            assert is_allowed is False
            assert "Try again in 30 seconds" in message
            mock_redis_client.exists.assert_called_once_with("rl:b:user123")

    @pytest.mark.asyncio
    async def test_is_allowed_blocked_user_negative_ttl(self):
        """Test is_allowed when user is blocked with negative TTL."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.return_value = True
            mock_redis_client.ttl.return_value = -1

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", block_duration=60
            )
            is_allowed, message = await limiter.is_allowed("user123")

            assert is_allowed is False
            assert "Try again in 60 seconds" in message

    @pytest.mark.asyncio
    async def test_is_allowed_rate_limit_exceeded(self):
        """Test is_allowed when rate limit is exceeded."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.return_value = False

            mock_pipeline = MagicMock()
            mock_pipeline.incr.return_value = mock_pipeline
            mock_pipeline.expire.return_value = mock_pipeline
            mock_pipeline.execute.return_value = [11, True]
            mock_redis_client.pipeline.return_value = mock_pipeline

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", max_requests=10
            )
            is_allowed, message = await limiter.is_allowed("user123")

            assert is_allowed is False
            assert "Blocked for 60 seconds" in message

    @pytest.mark.asyncio
    async def test_is_allowed_request_allowed(self):
        """Test is_allowed when request is allowed."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.return_value = False

            mock_pipeline = MagicMock()
            mock_pipeline.incr.return_value = mock_pipeline
            mock_pipeline.expire.return_value = mock_pipeline
            mock_pipeline.execute.return_value = [5, True]
            mock_redis_client.pipeline.return_value = mock_pipeline

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", max_requests=10
            )
            is_allowed, message = await limiter.is_allowed("user123")

            assert is_allowed is True
            assert "5 requests remaining" in message

    @pytest.mark.asyncio
    async def test_get_user_stats_with_data(self):
        """Test get_user_stats with existing data."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.get.return_value = "5"
            mock_redis_client.ttl.return_value = 30
            mock_redis_client.exists.return_value = True

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", max_requests=10
            )
            stats = await limiter.get_user_stats("user123")

            assert stats["requests"] == 5
            assert stats["remaining"] == 5
            assert stats["window_remaining"] == 30
            assert stats["blocked"] is True
            assert stats["blocked_until"] is not None

    @pytest.mark.asyncio
    async def test_get_user_stats_no_data(self):
        """Test get_user_stats with no existing data."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.get.return_value = None
            mock_redis_client.ttl.return_value = -1
            mock_redis_client.exists.return_value = False

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", max_requests=10
            )
            stats = await limiter.get_user_stats("user123")

            assert stats["requests"] == 0
            assert stats["remaining"] == 10
            assert stats["window_remaining"] == 60
            assert stats["blocked"] is False
            assert stats["blocked_until"] is None

    @pytest.mark.asyncio
    async def test_get_user_stats_blocked_ttl_zero(self):
        """Test get_user_stats when blocked but TTL is 0."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.get.return_value = "3"
            mock_redis_client.ttl.return_value = 20
            mock_redis_client.exists.return_value = True

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", max_requests=10
            )
            stats = await limiter.get_user_stats("user123")

            assert stats["requests"] == 3
            assert stats["remaining"] == 7
            assert stats["blocked"] is True
            assert stats["blocked_until"] is not None

    @pytest.mark.asyncio
    async def test_reset_user(self):
        """Test reset_user method."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
            await limiter.reset_user("user123")

            assert mock_redis_client.delete.call_count == 2
            mock_redis_client.delete.assert_any_call("rl:c:user123")
            mock_redis_client.delete.assert_any_call("rl:b:user123")

    @pytest.mark.asyncio
    async def test_get_global_stats(self):
        """Test get_global_stats method."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379",
                max_requests=10,
                window_seconds=60,
                block_duration=120,
            )
            stats = await limiter.get_global_stats()

            assert stats["total_users"] is None
            assert stats["active_users"] is None
            assert stats["blocked_users"] is None
            assert stats["max_requests_per_window"] == 10
            assert stats["window_seconds"] == 60
            assert stats["block_duration"] == 120

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test get_user_info method with success."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.return_value = False

            mock_pipeline = MagicMock()
            mock_pipeline.incr.return_value = mock_pipeline
            mock_pipeline.expire.return_value = mock_pipeline
            mock_pipeline.execute.return_value = [3, True]
            mock_redis_client.pipeline.return_value = mock_pipeline

            mock_redis_client.get.return_value = "3"
            mock_redis_client.ttl.return_value = 30

            limiter = RedisRateLimiter(
                redis_url="redis://localhost:6379", max_requests=10
            )
            info = await limiter.get_user_info("user123")

            assert info["user_id"] == "user123"
            assert info["rate_limited"] is False
            assert "Request allowed" in info["message"]
            assert info["remaining_requests"] == 7

    @pytest.mark.asyncio
    async def test_get_user_info_with_exception(self):
        """Test get_user_info method with exception."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.side_effect = Exception("Redis connection error")

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
            info = await limiter.get_user_info("user123")

            assert info["user_id"] == "user123"
            assert info["error"] == "Redis connection error"
            assert info["rate_limited"] is False
            assert info["remaining_requests"] == 0
            assert info["reset_time"] is None

    @pytest.mark.asyncio
    async def test_redis_rate_limiter_exception_handling(self):
        """Test RedisRateLimiter exception handling in is_allowed."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.exists.side_effect = Exception("Redis connection failed")

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")

            with pytest.raises(Exception, match="Redis connection failed"):
                await limiter.is_allowed("user123")

    @pytest.mark.asyncio
    async def test_redis_rate_limiter_get_user_stats_exception(self):
        """Test RedisRateLimiter exception in get_user_stats."""
        with patch("ttskit.utils.rate_limiter.redis") as mock_redis:
            mock_redis_client = MagicMock()
            mock_redis.from_url.return_value = mock_redis_client

            mock_redis_client.get.side_effect = Exception("Redis get failed")

            limiter = RedisRateLimiter(redis_url="redis://localhost:6379")

            with pytest.raises(Exception, match="Redis get failed"):
                await limiter.get_user_stats("user123")


class TestRateLimiterFunctions:
    """Test additional rate limiter functions."""

    @pytest.mark.asyncio
    async def test_get_rate_limit_stats(self):
        """Test get_rate_limit_stats function."""
        with patch("ttskit.utils.rate_limiter.rate_limiter") as mock_limiter:
            mock_limiter.get_user_stats = AsyncMock(
                return_value={"requests": 5, "remaining": 5}
            )

            result = await get_rate_limit_stats("user123")

            assert result == {"requests": 5, "remaining": 5}
            mock_limiter.get_user_stats.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_reset_rate_limit(self):
        """Test reset_rate_limit function."""
        with patch("ttskit.utils.rate_limiter.rate_limiter") as mock_limiter:
            mock_limiter.reset_user = AsyncMock()

            await reset_rate_limit("user123")

            mock_limiter.reset_user.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_global_rate_limit_stats(self):
        """Test get_global_rate_limit_stats function."""
        with patch("ttskit.utils.rate_limiter.rate_limiter") as mock_limiter:
            mock_limiter.get_global_stats = AsyncMock(return_value={"total_users": 10})

            result = await get_global_rate_limit_stats()

            assert result == {"total_users": 10}
            mock_limiter.get_global_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_global_stats_with_exception(self):
        """Test get_global_stats function with exception."""
        with patch("ttskit.utils.rate_limiter.rate_limiter") as mock_limiter:
            mock_limiter.get_global_stats = AsyncMock(
                side_effect=Exception("Database error")
            )

            result = await get_global_stats()

            assert result == {"error": "Database error"}

    @pytest.mark.asyncio
    async def test_get_user_info_function(self):
        """Test get_user_info function."""
        with patch("ttskit.utils.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, "Request allowed")

            result = await get_user_info("user123")

            assert result["user_id"] == "user123"
            assert result["rate_limited"] is False
            assert result["remaining_requests"] == "Request allowed"
            mock_check.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_user_info_function_with_exception(self):
        """Test get_user_info function with exception."""
        with patch(
            "ttskit.utils.rate_limiter.check_rate_limit",
            side_effect=Exception("Rate limit error"),
        ):
            result = await get_user_info("user123")

            assert result["user_id"] == "user123"
            assert result["error"] == "Rate limit error"
            assert result["rate_limited"] is False
            assert result["remaining_requests"] == 0
            assert result["reset_time"] is None

    @pytest.mark.asyncio
    async def test_is_rate_limited_function(self):
        """Test is_rate_limited function."""
        with patch("ttskit.utils.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (False, "Rate limit exceeded")

            result = await is_rate_limited("user123")

            assert result is True
            mock_check.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_is_rate_limited_function_allowed(self):
        """Test is_rate_limited function when allowed."""
        with patch("ttskit.utils.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, "Request allowed")

            result = await is_rate_limited("user123")

            assert result is False
            mock_check.assert_called_once_with("user123")


class TestCreateRateLimiter:
    """Test _create_rate_limiter function."""

    def test_create_rate_limiter_with_redis_enabled(self):
        """Test _create_rate_limiter with Redis enabled."""
        with (
            patch("ttskit.utils.rate_limiter.settings") as mock_settings,
            patch("ttskit.utils.rate_limiter._REDIS_AVAILABLE", True),
            patch("ttskit.utils.rate_limiter.RedisRateLimiter") as mock_redis_limiter,
        ):
            mock_settings.enable_rate_limiting = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.rate_limit_rpm = 10
            mock_settings.rate_limit_window = 60

            mock_redis_instance = MagicMock()
            mock_redis_limiter.return_value = mock_redis_instance

            result = _create_rate_limiter()

            assert result == mock_redis_instance
            mock_redis_limiter.assert_called_once_with(
                redis_url="redis://localhost:6379",
                max_requests=10,
                window_seconds=60,
                block_duration=60,
            )

    def test_create_rate_limiter_with_redis_disabled(self):
        """Test _create_rate_limiter with Redis disabled."""
        with (
            patch("ttskit.utils.rate_limiter.settings") as mock_settings,
            patch("ttskit.utils.rate_limiter._REDIS_AVAILABLE", True),
            patch("ttskit.utils.rate_limiter.RateLimiter") as mock_rate_limiter,
        ):
            mock_settings.enable_rate_limiting = False
            mock_settings.redis_url = "redis://localhost:6379"

            mock_limiter_instance = MagicMock()
            mock_rate_limiter.return_value = mock_limiter_instance

            result = _create_rate_limiter()

            assert result == mock_limiter_instance
            mock_rate_limiter.assert_called_once()

    def test_create_rate_limiter_with_no_redis_url(self):
        """Test _create_rate_limiter with no Redis URL."""
        with (
            patch("ttskit.utils.rate_limiter.settings") as mock_settings,
            patch("ttskit.utils.rate_limiter._REDIS_AVAILABLE", True),
            patch("ttskit.utils.rate_limiter.RateLimiter") as mock_rate_limiter,
        ):
            mock_settings.enable_rate_limiting = True
            mock_settings.redis_url = None

            mock_limiter_instance = MagicMock()
            mock_rate_limiter.return_value = mock_limiter_instance

            result = _create_rate_limiter()

            assert result == mock_limiter_instance
            mock_rate_limiter.assert_called_once()

    def test_create_rate_limiter_with_redis_unavailable(self):
        """Test _create_rate_limiter with Redis unavailable."""
        with (
            patch("ttskit.utils.rate_limiter.settings") as mock_settings,
            patch("ttskit.utils.rate_limiter._REDIS_AVAILABLE", False),
            patch("ttskit.utils.rate_limiter.RateLimiter") as mock_rate_limiter,
        ):
            mock_settings.enable_rate_limiting = True
            mock_settings.redis_url = "redis://localhost:6379"

            mock_limiter_instance = MagicMock()
            mock_rate_limiter.return_value = mock_limiter_instance

            result = _create_rate_limiter()

            assert result == mock_limiter_instance
            mock_rate_limiter.assert_called_once()

    def test_create_rate_limiter_with_redis_exception(self):
        """Test _create_rate_limiter with Redis initialization exception."""
        with (
            patch("ttskit.utils.rate_limiter.settings") as mock_settings,
            patch("ttskit.utils.rate_limiter._REDIS_AVAILABLE", True),
            patch("ttskit.utils.rate_limiter.RedisRateLimiter") as mock_redis_limiter,
            patch("ttskit.utils.rate_limiter.RateLimiter") as mock_rate_limiter,
            patch("logging.getLogger") as mock_logging_getter,
        ):
            mock_settings.enable_rate_limiting = True
            mock_settings.redis_url = "redis://localhost:6379"
            mock_settings.rate_limit_rpm = 10
            mock_settings.rate_limit_window = 60

            mock_redis_limiter.side_effect = Exception("Redis connection failed")

            mock_limiter_instance = MagicMock()
            mock_rate_limiter.return_value = mock_limiter_instance

            mock_logger = MagicMock()
            mock_logging_getter.return_value = mock_logger

            result = _create_rate_limiter()

            assert result == mock_limiter_instance
            mock_rate_limiter.assert_called_once()
            mock_logger.warning.assert_called_once()


class TestRateLimiterEdgeCases:
    """Test edge cases and additional scenarios."""

    @pytest.mark.asyncio
    async def test_rate_limiter_blocked_user_message(self):
        """Test rate limiter blocked user message."""
        limiter = RateLimiter(max_requests=1, window_seconds=60, block_duration=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        is_allowed, message = await limiter.is_allowed("user1")
        assert is_allowed is False
        assert "Try again in" in message

    @pytest.mark.asyncio
    async def test_rate_limiter_window_reset(self):
        """Test rate limiter window reset functionality."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is False

        stats = await limiter.get_user_stats("user1")
        assert stats["requests"] == 2
        assert stats["remaining"] == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_get_user_stats_new_user(self):
        """Test get_user_stats for new user."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        stats = await limiter.get_user_stats("newuser")

        assert stats["requests"] == 0
        assert stats["remaining"] == 5
        assert stats["blocked"] is False
        assert stats["blocked_until"] is None

    @pytest.mark.asyncio
    async def test_rate_limiter_get_user_info_exception(self):
        """Test get_user_info with exception."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        with patch.object(limiter, "is_allowed", side_effect=Exception("Test error")):
            info = await limiter.get_user_info("user1")

            assert info["user_id"] == "user1"
            assert info["error"] == "Test error"
            assert info["rate_limited"] is False
            assert info["remaining_requests"] == 0
            assert info["reset_time"] is None

    @pytest.mark.asyncio
    async def test_rate_limiter_get_user_stats_window_expired(self):
        """Test get_user_stats with expired window."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        await asyncio.sleep(1.1)

        stats = await limiter.get_user_stats("user1")

        assert stats["requests"] == 0
        assert stats["remaining"] == 5
        assert stats["blocked"] is False
        assert stats["blocked_until"] is None

    @pytest.mark.asyncio
    async def test_rate_limiter_get_global_stats_cleanup(self):
        """Test get_global_stats with cleanup of expired users."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user2")

        await asyncio.sleep(1.1)

        stats = await limiter.get_global_stats()

        assert stats["total_users"] == 0
        assert stats["active_users"] == 0
        assert stats["blocked_users"] == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_get_global_stats_with_blocked_users(self):
        """Test get_global_stats with blocked users."""
        limiter = RateLimiter(max_requests=1, window_seconds=60, block_duration=60)

        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")

        await limiter.is_allowed("user2")

        stats = await limiter.get_global_stats()

        assert stats["total_users"] == 2
        assert stats["active_users"] == 1
        assert stats["blocked_users"] == 1
