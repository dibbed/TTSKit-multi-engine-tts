# TTSKit API Documentation

## Overview

TTSKit provides a comprehensive REST API for text-to-speech synthesis with multiple engines, security features, and advanced capabilities.

## Features

- 🔐 **Authentication**: API key-based authentication with role-based permissions
- 🚦 **Rate Limiting**: Configurable rate limiting per client (default: 100 requests/minute)
- 🛡️ **Security**: CORS, security headers, input validation, trusted host middleware
- 🎤 **Multiple Engines**: Piper, Edge, GTTS support with smart routing
- 🌍 **Multi-language**: Support for multiple languages (en, fa, ar, etc.)
- 📦 **Batch Processing**: Synthesize multiple texts at once (up to 10 texts)
- 📊 **Monitoring**: Health checks, metrics, and comprehensive statistics
- 🔄 **Caching**: Intelligent caching for improved performance with Redis support
- 👥 **Admin Panel**: API key management and user administration
- 📈 **Metrics**: Real-time system metrics and performance monitoring

## Quick Start

### 1. Start the API Server

```bash
# Using uvicorn directly
uvicorn ttskit.api.app:app --host 0.0.0.0 --port 8000

# Or using the TTSKit CLI (recommended)
ttskit api --host 0.0.0.0 --port 8000

# Advanced CLI options
ttskit api --host 0.0.0.0 --port 8000 --workers 4 --reload --log-level debug
ttskit api --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### 2. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Synthesize text
curl -X POST http://localhost:8000/api/v1/synth \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-key" \
  -d '{"text": "Hello, world!", "lang": "en", "format": "wav"}' \
  --output audio.wav
```

## Authentication

The API supports Bearer token authentication:

```bash
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/api/v1/engines
```

### API Key Configuration

Set your API key in environment variables:

```bash
# Single API key (backward compatibility)
export TTSKIT_API_KEY="your-secret-key"
export TTSKIT_ENABLE_AUTH=true

# Multiple API keys with permissions
export TTSKIT_API_KEYS='{"admin": "admin-secret-key", "user1": "user1-key", "readonly_user": "readonly-key"}'
```

### Permission Levels

- **read**: Read-only access to public endpoints
- **write**: Read + write access (synthesis, cache management)
- **admin**: Full access including API key management

## Endpoints

### Synthesis Endpoints

#### POST `/api/v1/synth`

Synthesize text to speech audio.

**Authentication:** Optional (recommended for production)

**Request Body:**

```json
{
  "text": "Hello, world!",
  "lang": "en",
  "engine": "piper",
  "voice": "en_US-lessac-medium",
  "rate": 1.0,
  "pitch": 0.0,
  "format": "ogg"
}
```

**Parameters:**

- `text` (required): Text to synthesize (1-5000 characters)
- `lang` (optional): Language code (default: "en")
- `voice` (optional): Voice name (engine-specific)
- `engine` (optional): TTS engine to use (auto-selected if not specified)
- `rate` (optional): Speech rate multiplier (0.1-3.0, default: 1.0)
- `pitch` (optional): Pitch adjustment in semitones (-12.0 to 12.0, default: 0.0)
- `format` (optional): Output format - "ogg", "mp3", or "wav" (default: "ogg")

**Response:** Audio file (binary stream)

**Headers:**

- `Content-Type`: `audio/ogg`, `audio/mpeg`, or `audio/wav`
- `Content-Disposition`: `attachment; filename=synthesis.{format}`
- `X-Audio-Duration`: Duration in seconds
- `X-Audio-Size`: File size in bytes
- `X-Engine-Used`: Engine used for synthesis
- `X-Voice-Used`: Voice used for synthesis

#### POST `/api/v1/synth/batch`

Synthesize multiple texts to speech.

**Authentication:** Optional (recommended for production)

**Request Body:**

```json
{
  "texts": ["Hello", "World", "TTSKit"],
  "lang": "en",
  "engine": "piper",
  "voice": "en_US-lessac-medium",
  "rate": 1.0,
  "pitch": 0.0,
  "format": "ogg"
}
```

**Parameters:**

- `texts` (required): Array of texts to synthesize (1-10 texts)
- `lang` (optional): Language code (default: "en")
- `voice` (optional): Voice name (engine-specific)
- `engine` (optional): TTS engine to use
- `rate` (optional): Speech rate multiplier (0.1-3.0, default: 1.0)
- `pitch` (optional): Pitch adjustment in semitones (-12.0 to 12.0, default: 0.0)
- `format` (optional): Output format - "ogg", "mp3", or "wav" (default: "ogg")

**Response:**

```json
{
  "success": true,
  "total_texts": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "index": 0,
      "success": true,
      "text": "Hello",
      "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA...",
      "duration": 0.5,
      "size": 12345,
      "format": "ogg",
      "engine": "piper",
      "voice": "auto"
    },
    {
      "index": 1,
      "success": false,
      "error": "Text too long: 1500 characters (max: 1000)"
    }
  ]
}
```

#### GET `/api/v1/synth/preview`

Preview synthesis without getting audio file.

**Authentication:** Optional (recommended for production)

**Query Parameters:**

- `text` (required): Text to preview
- `lang` (optional): Language code (default: "en")
- `engine` (optional): Engine name
- `voice` (optional): Voice name

**Response:**

```json
{
  "success": true,
  "text_preview": "Hello, world!",
  "text_length": 13,
  "language": "en",
  "engine": "auto",
  "voice": "auto",
  "estimated_duration": 1.3,
  "available_engines": ["piper", "edge", "gtts"]
}
```

### Engine Endpoints

#### GET `/api/v1/engines`

List all available engines.

**Authentication:** Optional (recommended for production)

**Query Parameters:**

- `available_only` (optional): Show only available engines (default: false)

**Response:**

```json
[
  {
    "name": "piper",
    "available": true,
    "capabilities": {
      "offline": true,
      "ssml": false,
      "rate_control": true,
      "pitch_control": false,
      "max_text_length": 5000
    },
    "languages": ["en", "fa", "ar"],
    "voices": ["en_US-lessac-medium", "fa_IR-amir-medium"],
    "offline": true
  },
  {
    "name": "edge",
    "available": true,
    "capabilities": {
      "offline": false,
      "ssml": true,
      "rate_control": true,
      "pitch_control": true,
      "max_text_length": 1000
    },
    "languages": ["en", "fa", "ar"],
    "voices": ["en-US-AriaNeural", "fa-IR-DilaraNeural"],
    "offline": false
  }
]
```

#### GET `/api/v1/engines/{engine_name}`

Get detailed information about a specific engine.

**Authentication:** Optional (recommended for production)

**Response:** Same format as `/api/v1/engines` but for a single engine.

#### GET `/api/v1/engines/{engine_name}/voices`

List voices available for a specific engine.

**Authentication:** Optional (recommended for production)

**Query Parameters:**

- `language` (optional): Filter by language code

**Response:**

```json
[
  {
    "name": "en_US-lessac-medium",
    "engine": "piper",
    "language": "en",
    "gender": null,
    "quality": "medium",
    "sample_rate": 22050
  }
]
```

#### GET `/api/v1/voices`

List all available voices across all engines.

**Authentication:** Optional (recommended for production)

**Query Parameters:**

- `engine` (optional): Filter by engine name
- `language` (optional): Filter by language code

**Response:** Array of voice information objects.

#### GET `/api/v1/engines/{engine_name}/test`

Test a specific engine with sample text.

**Authentication:** Optional (recommended for production)

**Query Parameters:**

- `text` (optional): Test text (default: "Hello, world!")
- `language` (optional): Language code (default: "en")

**Response:**

```json
{
  "success": true,
  "engine": "piper",
  "test_text": "Hello, world!",
  "language": "en",
  "duration": 1.2,
  "size": 25000,
  "format": "wav",
  "message": "Engine 'piper' is working correctly"
}
```

#### GET `/api/v1/capabilities`

Get capabilities of all engines.

**Authentication:** Optional (recommended for production)

**Response:** Summary of what each engine can do.

### System Endpoints

#### GET `/health`

Public health check endpoint (no authentication required).

**Response:**

```json
{
  "status": "healthy",
  "engines": 3,
  "uptime": 3600.5,
  "version": "1.0.0"
}
```

#### GET `/api/v1/health`

Detailed health check endpoint.

**Authentication:** Required

**Response:** Same format as `/health` but with additional system checks.

#### GET `/api/v1/status`

Get detailed system status.

**Authentication:** Required

**Response:** Comprehensive system information including engine status, cache status, and system health.

#### GET `/api/v1/info`

Get system information.

**Authentication:** Required

**Response:** System details and configuration information.

#### GET `/api/v1/config`

Get current configuration.

**Authentication:** Required

**Response:** Current system configuration (sensitive data masked).

#### GET `/api/v1/cache/stats`

Get cache statistics.

**Authentication:** Required

**Response:**

```json
{
  "enabled": true,
  "hits": 1250,
  "misses": 300,
  "hit_rate": 0.806,
  "size": 52428800,
  "entries": 150
}
```

#### POST `/api/v1/cache/clear`

Clear cache.

**Authentication:** Required (write permission)

**Response:**

```json
{
  "message": "Cache cleared successfully"
}
```

#### GET `/api/v1/cache/enabled`

Check if cache is enabled.

**Authentication:** Required

**Response:**

```json
{
  "enabled": true
}
```

#### GET `/api/v1/formats`

Get supported audio formats.

**Authentication:** Required

**Response:**

```json
{
  "formats": ["ogg", "mp3", "wav"]
}
```

#### GET `/api/v1/languages`

Get supported language codes.

**Authentication:** Required

**Response:**

```json
{
  "languages": ["en", "fa", "ar", "es", "fr", "de"]
}
```

#### GET `/api/v1/rate-limit`

Get rate limit information.

**Authentication:** Required

**Response:** Current rate limit settings and usage statistics.

#### GET `/api/v1/documentation`

Get project documentation.

**Authentication:** Required

**Response:** API documentation and usage examples.

#### GET `/api/v1/metrics`

Get system metrics and performance data.

**Authentication:** Required

**Response:**

```json
{
  "tts_stats": {
    "total_synthesis": 1500,
    "successful_synthesis": 1480,
    "failed_synthesis": 20,
    "average_duration": 2.5
  },
  "system_metrics": {
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "disk_percent": 30.1,
    "process_count": 25,
    "uptime": 86400.5
  },
  "version": "0.1.0"
}
```

#### GET `/api/v1/version`

Get version information.

**Authentication:** Required

**Response:**

```json
{
  "version": "1.0.0",
  "service": "TTSKit API",
  "status": "running",
  "uptime": 86400.5
}
```

### Admin Endpoints

#### GET `/api/v1/admin/api-keys`

List all API keys (admin only).

**Authentication:** Required (admin permission)

**Response:**

```json
{
  "admin": {
    "user_id": "admin",
    "permissions": ["read", "write", "admin"],
    "created_at": "unknown"
  },
  "user1": {
    "user_id": "user1",
    "permissions": ["read", "write"],
    "created_at": "unknown"
  }
}
```

#### POST `/api/v1/admin/api-keys`

Create a new API key (admin only).

**Authentication:** Required (admin permission)

**Request Body:**

```json
{
  "user_id": "new_user",
  "api_key": "new-secret-key",
  "permissions": ["read", "write"]
}
```

**Response:**

```json
{
  "message": "API key created successfully for user 'new_user'",
  "user_id": "new_user",
  "permissions": ["read", "write"],
  "note": "In production, store this securely in a database"
}
```

#### PUT `/api/v1/admin/api-keys/{user_id}`

Update an existing API key (admin only).

**Authentication:** Required (admin permission)

**Request Body:**

```json
{
  "api_key": "updated-secret-key",
  "permissions": ["read", "write", "admin"]
}
```

**Response:**

```json
{
  "message": "API key updated successfully for user 'user1'",
  "user_id": "user1",
  "permissions": ["read", "write", "admin"],
  "note": "In production, update this securely in a database"
}
```

#### DELETE `/api/v1/admin/api-keys/{user_id}`

Delete an API key (admin only).

**Authentication:** Required (admin permission)

**Response:**

```json
{
  "message": "API key deleted successfully for user 'user1'",
  "note": "In production, remove this securely from database"
}
```

#### GET `/api/v1/admin/users/me`

Get current user information.

**Authentication:** Required (write permission)

**Response:**

```json
{
  "user_id": "admin",
  "permissions": ["read", "write", "admin"],
  "api_key": "admin-se..."
}
```

## CLI API Command

TTSKit provides a comprehensive CLI command for starting the API server with full uvicorn parameter support:

### Basic Usage

```bash
# Start API server with default settings
ttskit api

# Specify host and port
ttskit api --host 0.0.0.0 --port 8000

# Development mode with auto-reload
ttskit api --reload --log-level debug
```

### Advanced Options

```bash
# Production setup with multiple workers
ttskit api --host 0.0.0.0 --port 8000 --workers 4 --log-level info

# SSL/HTTPS setup
ttskit api --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem

# Custom headers and proxy settings
ttskit api --host 0.0.0.0 --port 8000 --header "X-Custom-Header: value" --proxy-headers

# Performance tuning
ttskit api --host 0.0.0.0 --port 8000 --workers 4 --timeout-keep-alive 30 --access-log
```

### Available Parameters

| Parameter                | Short | Default   | Description                                 |
| ------------------------ | ----- | --------- | ------------------------------------------- |
| `--host`                 | `-h`  | `0.0.0.0` | Host to bind to                             |
| `--port`                 | `-p`  | `8000`    | Port to bind to                             |
| `--workers`              | `-w`  | `1`       | Number of worker processes                  |
| `--reload`               |       | `False`   | Enable auto-reload for development          |
| `--log-level`            |       | `info`    | Log level (debug, info, warning, error)     |
| `--access-log`           |       | `True`    | Enable access logging                       |
| `--timeout-keep-alive`   |       | `5`       | Keep-alive timeout                          |
| `--ssl-keyfile`          |       | `None`    | SSL key file                                |
| `--ssl-certfile`         |       | `None`    | SSL certificate file                        |
| `--ssl-keyfile-password` |       | `None`    | SSL key file password                       |
| `--ssl-version`          |       | `None`    | SSL version                                 |
| `--ssl-cert-reqs`        |       | `None`    | SSL certificate requirements                |
| `--ssl-ca-certs`         |       | `None`    | SSL CA certificates file                    |
| `--ssl-ciphers`          |       | `None`    | SSL ciphers                                 |
| `--header`               |       | `[]`      | Custom headers (can be used multiple times) |
| `--forwarded-allow-ips`  |       | `None`    | Allowed forwarded IPs                       |
| `--root-path`            |       | `None`    | Root path                                   |
| `--proxy-headers`        |       | `True`    | Enable proxy headers                        |
| `--server-header`        |       | `True`    | Enable server header                        |
| `--date-header`          |       | `True`    | Enable date header                          |

### CLI Features

- **🎨 Beautiful Output**: Colorized and formatted output with emojis
- **📚 Auto Documentation**: Shows API documentation URLs
- **🔗 Quick Test**: Provides curl command for testing
- **⚙️ Full Control**: All uvicorn parameters supported
- **🛡️ SSL Support**: Complete SSL/TLS configuration
- **📊 Status Display**: Shows server configuration before starting

### Examples

```bash
# Development
ttskit api --reload --log-level debug --host localhost --port 3000

# Production
ttskit api --host 0.0.0.0 --port 8000 --workers 4 --log-level info --access-log

# HTTPS
ttskit api --host 0.0.0.0 --port 443 --ssl-keyfile /path/to/key.pem --ssl-certfile /path/to/cert.pem

# Behind proxy
ttskit api --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips "*"

# Custom headers
ttskit api --host 0.0.0.0 --port 8000 --header "X-API-Version: v1" --header "X-Custom: value"
```

## Configuration

### Environment Variables

```bash
# API Configuration
TTSKIT_API_KEY=your-secret-key
TTSKIT_ENABLE_AUTH=true
TTSKIT_API_RATE_LIMIT=100
TTSKIT_CORS_ORIGINS=["*"]
TTSKIT_ALLOWED_HOSTS=["*"]

# Multiple API Keys (JSON format)
TTSKIT_API_KEYS='{"admin": "admin-secret-key", "user1": "user1-key", "readonly_user": "readonly-key"}'

# TTS Configuration
TTSKIT_DEFAULT_LANG=en
TTSKIT_MAX_CHARS=1000
TTSKIT_MAX_TEXT_LENGTH=1000
TTSKIT_TTS_DEFAULT=edge

# Cache Configuration
TTSKIT_CACHE_ENABLED=true
TTSKIT_CACHE_TTL=3600
TTSKIT_CACHE_TYPE=memory

# Redis Configuration (optional)
TTSKIT_REDIS_URL=redis://localhost:6379
TTSKIT_REDIS_DB=0
TTSKIT_REDIS_PASSWORD=

# Logging Configuration
TTSKIT_LOG_LEVEL=INFO
TTSKIT_LOG_FORMAT=json
TTSKIT_LOG_FILE=logs/ttskit.log

# Performance Configuration
TTSKIT_MAX_WORKERS=4
TTSKIT_TIMEOUT=30
```

### Security Settings

```bash
# Enable authentication
TTSKIT_ENABLE_AUTH=true

# Set API key
TTSKIT_API_KEY=your-secret-key

# Configure CORS
TTSKIT_CORS_ORIGINS=["https://yourdomain.com"]

# Configure allowed hosts
TTSKIT_ALLOWED_HOSTS=["yourdomain.com", "api.yourdomain.com"]

# Rate limiting
TTSKIT_API_RATE_LIMIT=100  # requests per minute
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (validation errors, text too long)
- `401`: Unauthorized (invalid API key, authentication required)
- `403`: Forbidden (insufficient permissions, admin required)
- `404`: Not Found (engine not found, user not found)
- `409`: Conflict (user already exists)
- `422`: Validation Error (Pydantic validation errors)
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error
- `503`: Service Unavailable (engine not available)

### Error Response Format

```json
{
  "detail": "Error message",
  "error_type": "validation_error",
  "request_id": "12345"
}
```

### Common Error Scenarios

#### Text Too Long

```json
{
  "detail": "Text too long: 1500 characters (max: 1000)",
  "error_type": "text_too_long",
  "request_id": "12345"
}
```

#### Invalid API Key

```json
{
  "detail": "Invalid API key",
  "error_type": "authentication_error",
  "request_id": "12345"
}
```

#### Rate Limit Exceeded

```json
{
  "detail": "Rate limit exceeded",
  "error_type": "rate_limit_error",
  "request_id": "12345"
}
```

#### Engine Not Available

```json
{
  "detail": "Engine 'piper' is not available",
  "error_type": "engine_error",
  "request_id": "12345"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default**: 100 requests per minute per IP address
- **Configurable**: Via `TTSKIT_API_RATE_LIMIT` environment variable
- **Window**: 60 seconds rolling window
- **Scope**: Per client IP address
- **Headers**: Rate limit information included in responses:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets
  - `Retry-After`: Seconds to wait before retrying (on 429 error)

### Rate Limit Information Endpoint

Use `/api/v1/rate-limit` to get current rate limit settings and usage statistics.

## Caching

The API uses intelligent caching for improved performance:

- **Cache Key**: Based on text, language, engine, voice, rate, pitch, and format
- **Cache Types**: Memory cache (default) or Redis cache
- **TTL**: Configurable via `TTSKIT_CACHE_TTL` (default: 3600 seconds)
- **Statistics**: Available via `/api/v1/cache/stats`
- **Management**: Cache can be cleared via `/api/v1/cache/clear`
- **Status**: Check if cache is enabled via `/api/v1/cache/enabled`

### Cache Configuration

```bash
# Enable/disable caching
TTSKIT_CACHE_ENABLED=true

# Cache TTL in seconds
TTSKIT_CACHE_TTL=3600

# Cache type (memory or redis)
TTSKIT_CACHE_TYPE=memory

# Redis configuration (if using Redis cache)
TTSKIT_REDIS_URL=redis://localhost:6379
TTSKIT_REDIS_DB=0
```

## Monitoring

### Health Checks

- **`/health`**: Public health check (no authentication required)
- **`/api/v1/health`**: Detailed health check (authentication required)
- **`/api/v1/status`**: Comprehensive system status (authentication required)

### Metrics

- **`/api/v1/metrics`**: System metrics and performance data
- **`/api/v1/cache/stats`**: Cache performance statistics
- **`/api/v1/rate-limit`**: Rate limiting information and usage

### Logging

All API requests are logged with comprehensive information:

- **Request Details**: Method, URL, client IP, user agent
- **Response Details**: Status code, processing time, response size
- **Authentication**: User ID and permissions (if authenticated)
- **Error Details**: Full error information and stack traces
- **Performance**: Request timing and system metrics

### Security Headers

All responses include security headers:

- `X-Content-Type-Options`: nosniff
- `X-Frame-Options`: DENY
- `X-XSS-Protection`: 1; mode=block
- `Strict-Transport-Security`: max-age=31536000; includeSubDomains
- `Referrer-Policy`: strict-origin-when-cross-origin
- `Permissions-Policy`: geolocation=(), microphone=(), camera=()
- `X-API-Version`: API version
- `X-Service`: Service name
- `X-Process-Time`: Request processing time

## Examples

### Python Client

```python
import httpx
import asyncio

async def synthesize_text():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/synth",
            headers={"Authorization": "Bearer demo-key"},
            json={
                "text": "Hello, world!",
                "lang": "en",
                "format": "wav"
            }
        )
        return response.content

# Usage
audio_data = asyncio.run(synthesize_text())
```

### JavaScript Client

```javascript
async function synthesizeText() {
  const response = await fetch("http://localhost:8000/api/v1/synth", {
    method: "POST",
    headers: {
      Authorization: "Bearer demo-key",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text: "Hello, world!",
      lang: "en",
      format: "wav",
    }),
  });

  return await response.arrayBuffer();
}
```

### cURL Examples

```bash
# Basic synthesis
curl -X POST http://localhost:8000/api/v1/synth \
  -H "Authorization: Bearer demo-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!", "lang": "en", "format": "ogg"}' \
  --output audio.ogg

# Persian text with Piper engine
curl -X POST http://localhost:8000/api/v1/synth \
  -H "Authorization: Bearer demo-key" \
  -H "Content-Type: application/json" \
  -d '{"text": "سلام دنیا", "lang": "fa", "engine": "piper", "voice": "fa_IR-amir-medium", "format": "wav"}' \
  --output persian.wav

# Batch synthesis
curl -X POST http://localhost:8000/api/v1/synth/batch \
  -H "Authorization: Bearer demo-key" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello", "World"], "lang": "en", "format": "ogg"}' \
  | jq '.results[0].audio_base64' | base64 -d > batch.ogg

# Preview synthesis
curl -X GET "http://localhost:8000/api/v1/synth/preview?text=Hello%20world&lang=en&engine=piper" \
  -H "Authorization: Bearer demo-key"

# List engines
curl -X GET http://localhost:8000/api/v1/engines \
  -H "Authorization: Bearer demo-key"

# Get cache statistics
curl -X GET http://localhost:8000/api/v1/cache/stats \
  -H "Authorization: Bearer demo-key"

# Clear cache (requires write permission)
curl -X POST http://localhost:8000/api/v1/cache/clear \
  -H "Authorization: Bearer demo-key"

# Get system metrics
curl -X GET http://localhost:8000/api/v1/metrics \
  -H "Authorization: Bearer demo-key"
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "ttskit.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

1. **Security**:

   - Use strong, unique API keys for each user
   - Enable HTTPS with proper SSL certificates
   - Configure restrictive CORS origins
   - Set up firewall rules and IP whitelisting
   - Use trusted host middleware
   - Implement proper input validation
   - Regular security audits and updates

2. **Performance**:

   - Use Redis for distributed caching
   - Configure appropriate rate limits per user tier
   - Monitor system resources (CPU, memory, disk)
   - Optimize database queries and connections
   - Use connection pooling
   - Implement proper error handling and retries

3. **Monitoring**:

   - Set up comprehensive health checks
   - Monitor API metrics and performance
   - Configure alerting for critical issues
   - Use structured logging with proper log levels
   - Implement distributed tracing
   - Set up uptime monitoring

4. **Scaling**:

   - Use load balancers (nginx, HAProxy)
   - Deploy multiple API instances
   - Use container orchestration (Kubernetes, Docker Swarm)
   - Implement horizontal scaling
   - Use database clustering for high availability
   - Consider microservices architecture for large deployments

5. **Backup and Recovery**:

   - Regular database backups
   - Cache backup strategies
   - Disaster recovery procedures
   - Data retention policies

## Support

For issues and questions:

### Troubleshooting

1. **Check Service Status**:

   - Use `/health` endpoint for basic status
   - Use `/api/v1/status` for detailed system information
   - Check `/api/v1/metrics` for performance data

2. **Review Logs**:

   - Check application logs for error details
   - Monitor request/response logs
   - Look for authentication and rate limiting issues

3. **API Documentation**:

   - Interactive docs available at `/docs`
   - OpenAPI specification at `/openapi.json`
   - ReDoc documentation at `/redoc`

4. **Common Issues**:
   - **401 Unauthorized**: Check API key configuration
   - **429 Too Many Requests**: Rate limit exceeded, wait and retry
   - **400 Bad Request**: Check request format and parameters
   - **503 Service Unavailable**: Engine not available, check engine status

### Getting Help

- **Documentation**: Review this API documentation
- **Health Checks**: Use monitoring endpoints
- **System Information**: Check `/api/v1/info` and `/api/v1/config`
- **Engine Status**: Use `/api/v1/engines` to check engine availability
- **Cache Status**: Check `/api/v1/cache/stats` for cache performance

### API Limits

- **Text Length**: Maximum 1000 characters per request (configurable)
- **Batch Size**: Maximum 10 texts per batch request
- **Rate Limit**: 100 requests per minute per IP (configurable)
- **Audio Formats**: ogg, mp3, wav
- **Supported Languages**: en, fa, ar, es, fr, de (varies by engine)
