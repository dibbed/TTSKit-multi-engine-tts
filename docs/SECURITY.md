# 🔒 TTSKit Security Guide

## Overview

TTSKit implements comprehensive security measures to protect user data, API keys, and system resources. This document outlines the actual security features implemented in the project.

## 🔑 API Key Security

### Enhanced Security Features

- **Hash-Only Storage**: API keys are stored only as SHA-256 hashes with salt
- **No Plain Text**: Plain text API keys are never stored in the database
- **Usage Tracking**: Monitor API key usage patterns for security
- **Expiration Support**: API keys can have expiration dates
- **Secure Generation**: Cryptographically secure random key generation

### API Key Lifecycle

1. **Generation**: `ttskit_` + 32 random characters
2. **Hashing**: SHA-256 with salt (`ttskit_salt_2024`)
3. **Storage**: Only hash stored in database
4. **Verification**: Hash comparison for authentication
5. **Cleanup**: Plain text discarded after creation

### Example Usage

```python
from ttskit.services.user_service import UserService
from ttskit.database.connection import get_async_session

async def create_secure_api_key():
    async for db_session in get_async_session():
        user_service = UserService(db_session)

        # Create API key (returns plain text once)
        api_key_data = await user_service.create_api_key(
            user_id="user123",
            permissions=["read", "write"],
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        # Save the plain key securely!
        plain_key = api_key_data["api_key"]
        print(f"Save this key: {plain_key}")

        # Verify API key
        user_info = await user_service.verify_api_key(plain_key)
        if user_info:
            print(f"Authenticated user: {user_info['user_id']}")
```

## 🛡️ Security Middleware

### Security Headers

TTSKit automatically adds security headers to all API responses:

```python
# Security headers added by SecurityHeadersMiddleware
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
```

### Request Logging

All requests are logged with security information:

```python
# Request logging includes:
# - Client IP address
# - Request method and URL
# - User-Agent header
# - Response status and processing time
logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
```

### Error Handling

Unhandled exceptions are caught and logged securely:

```python
# Prevents stack trace exposure
# Returns standardized JSON error responses
# Logs errors for security monitoring
```

## 🚦 Rate Limiting

### Built-in Rate Limiting

TTSKit includes comprehensive rate limiting:

```python
from ttskit.utils.rate_limiter import RateLimiter

# Create rate limiter instance
rate_limiter = RateLimiter(
    max_requests=100,  # Default: 100 requests per minute
    window_seconds=60,
    block_duration=60  # Block for 60 seconds after limit exceeded
)

# Check if request is allowed
if rate_limiter.is_allowed("user123"):
    # Process request
    pass
else:
    # Rate limit exceeded
    pass
```

### Redis Support

For production deployments, Redis-backed rate limiting is available:

```python
from ttskit.utils.rate_limiter import RedisRateLimiter

# Redis-backed rate limiter
redis_limiter = RedisRateLimiter(
    redis_url="redis://localhost:6379",
    max_requests=100,
    window_seconds=60
)
```

## 🔐 Authentication & Authorization

### API Key Authentication

TTSKit uses Bearer token authentication:

```bash
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/api/v1/engines
```

### Permission System

- **read**: Read access to TTS services
- **write**: Write access to TTS services
- **admin**: Administrative access
- **delete**: Delete operations
- **manage**: User management

### User Management

```python
# Create user
user = await user_service.create_user(
    user_id="user123",
    username="John Doe",
    email="john@example.com",
    is_admin=False
)

# Update user
await user_service.update_user(
    user_id="user123",
    is_active=True,
    is_admin=False
)
```

## 🗄️ Database Security

### Configuration Priority

1. **Config Settings**: First priority from `config.py`
2. **Environment Variables**: Second priority from `.env`
3. **Defaults**: Fallback values

### Secure Configuration

```python
# config.py
class Settings(BaseSettings):
    # Database security settings
    database_url: str | None = None
    database_path: str = "ttskit.db"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
```

### Connection Security

- **Connection Pooling**: Configurable pool sizes
- **Pre-ping**: Automatic connection health checks
- **Transaction Safety**: Proper rollback on errors
- **Session Management**: Automatic cleanup

## 🚨 Security Monitoring

### Logging

All security events are logged with appropriate levels:

```python
# Security events are automatically logged
logger.warning(f"Security Event: {event_type} - User: {user_id}")
```

### Usage Tracking

- **Usage Count**: Track API key usage frequency
- **Last Used**: Timestamp of last usage
- **IP Tracking**: Client IP address logging
- **Session Management**: Track user sessions

## 🔧 Migration & Updates

### Database Migration

Run the migration script to update existing databases:

```bash
python -m ttskit.database.migration
```

### Security Checklist

- [ ] Remove plain text API keys from database
- [ ] Enable usage tracking
- [ ] Set up proper logging
- [ ] Configure rate limiting
- [ ] Update API key permissions
- [ ] Test security features

## 🧪 Testing Security

### Run Security Tests

```bash
# Run all tests including security tests
pytest tests/

# Run specific security-related tests
pytest tests/test_database_migration.py
pytest tests/test_rate_limiter.py
```

### Test Coverage

- API key generation and verification
- Hash consistency
- Rate limiting functionality
- Database security
- Middleware security headers

## 📋 Best Practices

### For Developers

1. **Never log API keys** in plain text
2. **Use secure random** for key generation
3. **Validate all inputs** before processing
4. **Implement rate limiting** on all endpoints
5. **Monitor usage patterns** for anomalies
6. **Use HTTPS** in production
7. **Regular security audits**

### For Administrators

1. **Rotate API keys** regularly
2. **Monitor access logs** for suspicious activity
3. **Set appropriate expiration** dates
4. **Use least privilege** principle
5. **Keep dependencies updated**
6. **Backup securely** with encryption

## 🚀 Production Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/ttskit
DATABASE_ECHO=false
DATABASE_POOL_SIZE=10

# Security
API_RATE_LIMIT=100
ENABLE_AUTH=true
CORS_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### Docker Security

```dockerfile
# Use non-root user
USER 1000:1000

# Set security headers
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
```

## 🔍 Security Audit

### Regular Checks

1. **API Key Rotation**: Monthly
2. **Permission Review**: Quarterly
3. **Access Log Analysis**: Weekly
4. **Dependency Updates**: Monthly
5. **Security Testing**: Before releases

### Incident Response

1. **Immediate**: Revoke compromised API keys
2. **Short-term**: Analyze access logs
3. **Long-term**: Update security measures

## 📞 Support

For security issues or questions:

- **Email**: security@ttskit.local
- **Issues**: GitHub security advisory
- **Documentation**: This guide

---

**⚠️ Important**: Always keep your API keys secure and never commit them to version control!
