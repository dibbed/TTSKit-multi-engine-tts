# TTSKit Architecture

## System Overview

```mermaid
graph TD
    U[User] -->|Telegram| TG[Telegram Bot]
    U2[User/Dev] -->|CLI| CLI[ttskit CLI]
    U3[Client] -->|HTTP| API[FastAPI]

    subgraph Adapters
        TG --> A1[aiogram]
        TG --> A2[pyrogram]
        TG --> A3[telethon]
        TG --> A4[telebot]
    end

    A1 --> CORE[UnifiedBot / Public API]
    A2 --> CORE
    A3 --> CORE
    A4 --> CORE
    CLI --> CORE
    API --> CORE

    subgraph Core
        CORE --> PARSE[parsing & validate]
        PARSE --> ROUTER[Engine Router]
        ROUTER --> CACHE{Cache}
        CACHE -->|hit| OUT1[(Audio Out)]
        CACHE -->|miss| ENG[Engines]
        ENG --> PIPE[Audio Pipeline]
        PIPE --> FF[FFmpeg/OGG Opus]
        FF --> OUT1
        OUT1 --> SEND[Telegram/HTTP/File]
    end

    subgraph Storage
        CACHE2[Redis / Memory]
        DB[(SQLite / PostgreSQL)]
    end

    CACHE -. uses .-> CACHE2
    CORE -. users/services .-> DB

    subgraph Engines
        E1[gTTS]
        E2[Edge TTS]
        E3[Piper]
    end
    ENG --> E1
    ENG --> E2
    ENG --> E3

    subgraph Ops
        HLTH[Health Checker]
        METRICS[Metrics/Prometheus]
        RL[Rate Limiter]
        CFG[Settings (Pydantic)]
        TMP[Temp Manager]
    end

    CORE -. config .-> CFG
    CORE -. metrics .-> METRICS
    CORE -. limits .-> RL
    CORE -. temp .-> TMP
    API -. health .-> HLTH
```

## Component Details

### 1. **Multi-Framework Telegram Bot**

- **Supported Frameworks**: aiogram v3, pyrogram, telethon, telebot
- **Unified Interface**: Single bot class works with any framework
- **Command Processing**: `/voice fa: سلام`, `/health`, `/admin`
- **Error Handling**: Comprehensive error handling and user feedback
- **Admin Panel**: Built-in admin commands for system management

### 2. **Smart Engine Router**

- **Multi-Engine Support**: gTTS, Edge TTS, Piper TTS
- **Language-Specific Routing**: Different engines for different languages
- **Fallback Mechanism**: Automatic fallback when primary engine fails
- **Performance Tracking**: Engine performance metrics and selection
- **Configuration-Based**: Policy-driven engine selection

### 3. **Advanced Cache System**

- **Multi-Tier Caching**: Redis + Memory fallback
- **Intelligent Key Generation**: SHA256-based cache keys
- **Configurable TTL**: Per-engine cache expiration
- **Cache Statistics**: Hit/miss ratios and performance metrics
- **Cache Management**: Admin commands for cache control

### 4. **Audio Processing Pipeline**

- **Format Support**: OGG, MP3, WAV output formats
- **Quality Enhancement**: Audio normalization and effects
- **FFmpeg Integration**: Professional audio processing
- **Sample Rate Control**: Configurable audio quality (8kHz-192kHz)
- **Channel Support**: Mono and stereo output

### 5. **Security & Authentication**

- **API Key Management**: Hash-based secure storage
- **Role-Based Access**: Read, write, admin permissions
- **Rate Limiting**: Per-user request limiting
- **Input Validation**: Comprehensive input sanitization
- **CORS Support**: Configurable cross-origin policies

### 6. **Database Layer**

- **SQLite Default**: Lightweight local database
- **PostgreSQL Support**: Production-ready database support
- **User Management**: User accounts and permissions
- **API Key Storage**: Secure hash-only storage
- **Migration System**: Automatic database schema updates

### 7. **REST API**

- **FastAPI Framework**: Modern async API
- **OpenAPI Documentation**: Auto-generated API docs
- **Authentication**: Bearer token authentication
- **Batch Processing**: Multiple text synthesis
- **Health Endpoints**: System monitoring and status

### 8. **Monitoring & Metrics**

- **Health Checks**: System health monitoring
- **Performance Metrics**: Engine and system statistics
- **Usage Tracking**: API key usage monitoring
- **Error Logging**: Comprehensive error tracking
- **Real-time Stats**: Live system performance data
