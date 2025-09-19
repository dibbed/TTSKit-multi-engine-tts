# 🚀 TTSKit Advanced Features

This document describes the advanced features of TTSKit including performance optimization, advanced monitoring, and Telegram admin panel.

## 📊 Performance Optimization

### Connection Pooling

```python
from ttskit.utils.performance import ConnectionPool, PerformanceConfig

# Performance optimization settings
config = PerformanceConfig(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30.0,
    max_concurrent_requests=10
)

# Using connection pool
pool = ConnectionPool(config)
response = await pool.request("GET", "https://api.example.com/data")
```

### Parallel Processing

```python
from ttskit.utils.performance import ParallelProcessor

# Parallel processing
processor = ParallelProcessor(max_workers=5)
results = await processor.process_batch(items, process_function)
```

### Memory Optimization

```python
from ttskit.utils.performance import MemoryOptimizer

# Memory optimization
optimizer = MemoryOptimizer(config)
memory_info = optimizer.get_memory_usage()
```

## 📈 Advanced Metrics

### Comprehensive Metrics Collection

```python
from ttskit.metrics.advanced import get_metrics_collector

# Comprehensive metrics collection
collector = get_metrics_collector()
metrics = await collector.get_comprehensive_metrics()

# Engine comparison
comparison = await collector.get_engine_comparison()

# Language analytics
analytics = await collector.get_language_analytics()
```

### Real-time Monitoring

```python
from ttskit.metrics.advanced import start_metrics_collection

# Start real-time monitoring
await start_metrics_collection(interval_seconds=60)
```

## 🤖 Telegram Admin Panel

### Setting up Admin Bot

```python
from ttskit.bot.unified_bot import UnifiedTTSBot

# Start bot with admin features
admin_ids = [123456789, 987654321]  # Telegram user IDs
await start_admin_bot("YOUR_BOT_TOKEN", admin_ids)
```

### Admin Commands

#### Main Commands:

- `/admin` - Main admin panel
- `/stats` - System statistics
- `/health` - System health check
- `/performance` - Performance analysis

#### API Key Management:

- `/create_key user_id:admin permissions:read,write,admin`
- `/list_keys` - List all keys
- `/delete_key user_id:old_user`

#### Cache Management:

- `/clear_cache` - Clear cache
- `/monitor` - Real-time monitoring

#### Debug:

- `/debug` - Debug information
- `/test_engines` - Test engines

### Admin Panel Features

#### 📊 System Statistics

- Request count
- Success rate
- Engine statistics
- Cache status
- System resources

#### 🔑 API Key Management

- Create new keys
- List all keys
- Delete keys
- Set permissions

#### 🔄 Cache Management

- View cache statistics
- Clear cache
- Set TTL

#### 🎤 Engine Testing

- Test all engines
- Test specific engine
- Performance reports

## 🔧 New API Endpoints

### Advanced Metrics

```http
GET /api/v1/advanced-metrics
Authorization: Bearer YOUR_API_KEY
```

**Response:**

```json
{
  "comprehensive": {
    "requests": {
      "total": 1500,
      "success_rate": 98.5,
      "per_minute": 25.0
    },
    "engines": {
      "edge": {
        "total_requests": 800,
        "success_rate": 99.2,
        "avg_response_time": 1.2
      }
    },
    "cache": {
      "hit_rate": 85.2,
      "size_mb": 125.5
    },
    "system": {
      "cpu_percent": 15.2,
      "memory_percent": 45.8
    },
    "health": 92.5
  },
  "engine_comparison": {
    "edge": {
      "reliability_score": 95.0,
      "performance_score": 88.5
    }
  },
  "language_analytics": {
    "fa": {
      "usage_percentage": 40.0,
      "preferred_engines": ["edge", "piper"]
    }
  }
}
```

## 🚀 Production Usage

### Recommended Settings

```python
# config.py
class Settings:
    # Performance
    max_connections: int = 100
    max_concurrent_requests: int = 10
    memory_limit_mb: int = 512

    # Metrics
    metrics_collection_interval: int = 60
    metrics_history_size: int = 1000

    # Admin
    admin_ids: List[int] = [123456789]
    enable_admin_panel: bool = True
```

### Docker Compose

```yaml
version: "3.8"
services:
  ttskit:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - ADMIN_IDS=${ADMIN_IDS}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  ttskit-api:
    build: .
    command: ttskit api --host 0.0.0.0 --port 8000
    environment:
      - REDIS_URL=redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## 📝 Examples

### Complete Admin Bot Example

```python
# admin_bot_example.py
import asyncio
from ttskit.bot.unified_bot import UnifiedTTSBot

async def main():
    bot_token = "YOUR_BOT_TOKEN"
    admin_ids = [123456789]  # Your Telegram user ID

    await start_admin_bot(bot_token, admin_ids)

if __name__ == "__main__":
    asyncio.run(main())
```

### Performance Optimization Example

```python
# performance_example.py
import asyncio
from ttskit.utils.performance import ParallelProcessor
from ttskit.public import TTS

async def batch_synthesis():
    tts = TTS()
    processor = ParallelProcessor(max_workers=5)

    texts = ["Text 1", "Text 2", "Text 3"]

    async def synthesize(text):
        return await tts.synth_async(text, lang="en")

    results = await processor.process_batch(texts, synthesize)
    return results

asyncio.run(batch_synthesis())
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Connection Pool Error

```
Error: Connection pool exhausted
```

**Solution:** Increase `max_connections` in settings

#### 2. Memory Error

```
Error: Memory limit exceeded
```

**Solution:** Reduce `memory_limit_mb` or increase RAM

#### 3. Admin Access Error

```
Error: Access denied
```

**Solution:** Check `admin_ids` in settings

### Logs

```bash
# View logs
tail -f logs/ttskit.log

# Debug mode
export LOG_LEVEL=DEBUG
```

## 📚 Additional Resources

- [API Documentation](api.md)
- [Architecture Overview](architecture.md)
- [Performance Best Practices](performance.md)
- [Admin Panel Guide](admin_panel.md)

## 🤝 Contributing

To report bugs or suggest new features:

1. Create an issue
2. Submit a pull request
3. Contact the team

---

**Note:** These features are designed for production environments and require proper configuration.
