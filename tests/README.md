# TTSKit Tests

This directory contains comprehensive tests for TTSKit with different performance levels.

## Test Categories

### 🚀 Fast Tests (`test-fast`)

- Unit tests with mocked dependencies
- API validation tests
- Basic functionality tests
- **Duration**: ~30 seconds

### ⚡ Balanced Tests (`test`)

- Mix of unit and integration tests
- Some real engine tests
- Performance optimizations applied
- **Duration**: ~2-3 minutes

### 🐌 Slow Tests (`test-slow`)

- Real engine integration tests
- Performance tests
- Comprehensive API tests
- **Duration**: ~5-10 minutes

### 🔧 Real Engine Tests (`test-real`)

- Tests with actual TTS engines
- End-to-end synthesis tests
- Engine capability tests
- **Duration**: ~10-15 minutes

## Running Tests

### Quick Development Testing

```bash
make test-fast
# or
pytest tests/ -m "not slow"
```

### Balanced Testing (Recommended)

```bash
make test
# or
pytest tests/
```

### Comprehensive Testing

```bash
make test-real
# or
pytest tests/ --real-engines
```

### Specific Test Categories

```bash
make test-api          # API tests only
make test-public       # Public API tests only
make test-bot          # Bot command tests only
make test-real-engines # Real engine tests only
make test-performance  # Performance tests only
```

## Test Files

### Core Tests

- `test_api_advanced.py` - Advanced API tests (optimized)
- `test_public.py` - Public API tests (optimized)
- `test_bot_commands.py` - Bot command tests (optimized)

### Real Engine Tests

- `test_real_engines.py` - Real engine integration tests
- `test_piper_engine.py` - Piper engine specific tests
- `test_performance.py` - Performance and load tests

### Configuration

- `conftest.py` - Test configuration and fixtures
- `Makefile` - Test commands and shortcuts

## Performance Optimizations

### Applied Optimizations

1. **Reduced test combinations** - Fewer parameter combinations
2. **Mocked heavy operations** - Mocked engine loading where appropriate
3. **Fast audio pipeline** - Skip processing for small test data
4. **Selective engine testing** - Test only available engines
5. **Cached engine instances** - Reuse engine instances where possible

### Test Data Optimization

- Small audio files (< 1KB) skip audio processing
- Mocked voice lists for faster testing
- Reduced text samples for synthesis tests

## Environment Variables

```bash
# Enable fast test mode
export TTSKIT_TEST_FAST=true

# Enable real engine tests
export TTSKIT_TEST_REAL_ENGINES=true

# Skip slow tests
export TTSKIT_SKIP_SLOW=true

# Disable cache in tests
export TTSKIT_CACHE_ENABLED=false
```

## Test Markers

```python
@pytest.mark.slow          # Slow tests (skip with -m "not slow")
@pytest.mark.integration   # Integration tests
@pytest.mark.real_engine   # Real engine tests (skip without --real-engines)
```

## CI/CD Integration

### GitHub Actions

```yaml
# Fast tests for PRs
- name: Run Fast Tests
  run: make test-fast

# Comprehensive tests for main branch
- name: Run Full Tests
  run: make test-ci
```

### Local Development

```bash
# Quick feedback loop
make test-dev

# Before committing
make test

# Before releasing
make test-real
```

## Troubleshooting

### Slow Tests

If tests are running slowly:

1. Use `make test-fast` for development
2. Check if real engines are being loaded unnecessarily
3. Verify audio pipeline optimizations are working

### Engine Availability

If engines are not available:

1. Install required dependencies
2. Check engine-specific requirements
3. Use `make test-real-engines` to test only available engines

### Memory Issues

If tests consume too much memory:

1. Use `make test-fast` to avoid heavy tests
2. Check for memory leaks in engine loading
3. Verify audio pipeline memory optimizations

## Contributing

When adding new tests:

1. Use appropriate markers (`@pytest.mark.slow`, etc.)
2. Optimize for fast execution when possible
3. Add real engine tests for critical functionality
4. Update this README if adding new test categories
