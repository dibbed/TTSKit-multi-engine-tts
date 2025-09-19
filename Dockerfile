# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    gcc \
    g++ \
    libsndfile1 \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY ttskit/ ttskit/
COPY ttskit_cli/ ttskit_cli/
COPY examples/ examples/
COPY models/ models/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install all dependencies from requirements.txt
RUN pip install --no-cache-dir \
    gTTS>=2.5 \
    edge-tts>=6.1 \
    pydub>=0.25 \
    librosa>=0.10.0 \
    soundfile>=0.12.0 \
    numpy>=1.24.0 \
    onnx>=1.14.0 \
    onnxruntime>=1.15.0 \
    aiogram>=3.0 \
    pyrogram>=2.0 \
    telethon>=1.30 \
    pyTelegramBotAPI>=4.0 \
    pydantic>=2.0 \
    pydantic-settings>=2.3 \
    python-dotenv>=1.0 \
    typer>=0.12 \
    fastapi>=0.100.0 \
    uvicorn>=0.20.0 \
    SQLAlchemy>=2.0.0 \
    redis>=4.0.0 \
    requests>=2.28.0 \
    httpx>=0.24.0 \
    aiofiles>=23.0.0 \
    asyncio-mqtt>=0.13.0 \
    psutil>=5.8.0 \
    prometheus-client>=0.17.0 \
    aiosqlite>=0.19.0

# Install the main package
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Set environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TTSKIT_DEFAULT_LANG=en
ENV TTSKIT_CACHE_ENABLED=true
ENV TTSKIT_RATE_LIMITING=true

# Expose port for API
EXPOSE 8080

# Health check: synth a short sample and ensure non-empty output
HEALTHCHECK --interval=30s --timeout=15s --start-period=10s --retries=3 \
    CMD python -c "import sys; from ttskit import synth; a=synth('سلام','fa', output_format='ogg'); sys.exit(0 if (hasattr(a,'data') and a.data) else 1)"

# Default command (can be overridden)
CMD ["ttskit", "--help"]
