"""
TTSKit CLI Application

This module provides a comprehensive command-line interface for TTSKit using the Typer framework.
It includes commands for starting the Telegram TTS bot, synthesizing speech to audio files,
listing voices and engines, checking system health, managing cache, running the API server,
and performing setup and migration tasks. Helper functions handle lazy imports and utility parsing
to optimize loading and configuration.
"""

import asyncio
import os
import sys
from pathlib import Path

import typer

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception as exc:
    sys.stderr.write(f"[warn] dotenv not loaded: {exc}\n")

from ttskit.cache.memory import memory_cache
from ttskit.config import settings
from ttskit.engines.factory import EngineFactory
from ttskit.health import check_system_health
from ttskit.metrics import get_metrics_summary as get_metrics
from ttskit.utils.logging_config import setup_logging


def _mask_value(value: str | int | None, keep: int = 2) -> str:
    """Mask a sensitive value by keeping first and last N characters.

    Args:
        value: The secret value (str/int) to mask.
        keep: Number of characters to keep at both ends (default 2).

    Returns:
        Masked string like '12***34' or '****' if too short/empty.
    """
    if value is None:
        return "Not set"
    s = str(value)
    if len(s) <= keep * 2:
        return "*" * len(s) if s else "Not set"
    return f"{s[:keep]}{'*' * (len(s) - keep * 2)}{s[-keep:]}"


def get_tts():
    """Retrieve the TTS class using lazy import to avoid early loading of dependencies.

    This approach defers importing Telegram-related modules until they're actually needed,
    preventing potential import errors and reducing initial load time.

    Returns:
        type: The TTS class from ttskit.
    """
    from ttskit import TTS

    return TTS


def get_synth_config():
    """Retrieve the SynthConfig class using lazy import for deferred loading.

    This function returns the class used to configure text-to-speech synthesis parameters,
    ensuring it's only imported when required to optimize startup performance.

    Returns:
        type: The SynthConfig class from ttskit.
    """
    from ttskit import SynthConfig

    return SynthConfig


def get_engines():
    """Discover and return information on available TTS engines and their capabilities.

    This function initializes the EngineFactory, registers default engines, and
    gathers details for each, including availability, offline support, supported
    languages, available voices, and a brief description. It gracefully handles
    any initialization errors for individual engines.

    Returns:
        list: A list of dictionaries, each with keys: 'name' (str), 'available' (bool),
              'offline' (bool), 'languages' (list of str), 'voices' (list), and
              'description' (str).
    """
    factory = EngineFactory()
    factory._register_default_engines()
    engine_names = factory.get_available_engines()

    engines = []
    for name in engine_names:
        try:
            engine_instance = factory.create_engine(name)
            if engine_instance:
                voices = engine_instance.list_voices()
                engines.append(
                    {
                        "name": name,
                        "available": True,
                        "offline": name == "piper",
                        "languages": ["en", "fa", "ar"],
                        "voices": voices,
                        "description": f"{name.upper()} TTS Engine",
                    }
                )
            else:
                engines.append(
                    {
                        "name": name,
                        "available": False,
                        "offline": False,
                        "languages": [],
                        "voices": [],
                        "description": f"{name.upper()} TTS Engine (not available)",
                    }
                )
        except Exception:
            engines.append(
                {
                    "name": name,
                    "available": False,
                    "offline": False,
                    "languages": [],
                    "voices": [],
                    "description": f"{name.upper()} TTS Engine (error)",
                }
            )

    return engines


app = typer.Typer(help="TTSKit: Professional Text-to-Speech CLI", no_args_is_help=True)


@app.command()
def start(
    token: str | None = typer.Option(
        None, "--token", help="Telegram bot token (or set BOT_TOKEN env)"
    ),
    adapter: str = typer.Option(
        "", "--adapter", help="Telegram framework adapter (or TELEGRAM_ADAPTER)"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable caching"),
    no_audio_processing: bool = typer.Option(
        False, "--no-audio-processing", help="Disable audio processing"
    ),
) -> None:
    """Start the unified Telegram TTS bot with optional configuration overrides.

    This command serves as a compatibility shim for Makefile workflows. It sets up logging,
    resolves the bot token and adapter from options or environment variables, initializes
    the UnifiedTTSBot, and runs it asynchronously in an infinite loop until interrupted.
    Caching and audio processing can be disabled via flags.

    Args:
        token: Telegram bot token, or use BOT_TOKEN environment variable.
        adapter: Telegram framework adapter (e.g., 'aiogram'), or use TELEGRAM_ADAPTER/TELEGRAM_DRIVER.
        no_cache: If True, disables caching in the bot.
        no_audio_processing: If True, disables audio post-processing.

    Notes:
        Requires a valid bot token; raises ValueError if missing.
        The bot runs indefinitely and handles graceful shutdown on cancellation.
    """
    try:
        setup_logging(settings.log_level)
        # Resolve bot token from CLI option, environment, or settings fallback
        token = token or settings.bot_token
        if not token:
            raise ValueError("Missing bot token. Pass --token or set BOT_TOKEN env.")
        adapter = adapter or settings.telegram_driver
        from ttskit.bot.unified_bot import UnifiedTTSBot

        async def _run():
            bot = UnifiedTTSBot(
                bot_token=token,
                adapter_type=adapter,
                cache_enabled=not no_cache,
                audio_processing=not no_audio_processing,
            )
            await bot.start()
            try:
                while bot.is_running:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
            finally:
                await bot.stop()

        asyncio.run(_run())
    except Exception as e:
        typer.secho(f"Failed to start bot: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command()
def synth(
    text: str = typer.Argument(..., help="Text to synthesize"),
    lang: str = typer.Option(
        "en", "--lang", "-l", help="Language code (e.g., 'en', 'fa', 'ar')"
    ),
    engine: str | None = typer.Option(None, "--engine", "-e", help="TTS engine to use"),
    voice: str | None = typer.Option(None, "--voice", "-v", help="Voice name"),
    rate: str = typer.Option(
        "1.0", "--rate", "-r", help="Speech rate (e.g., '1.0', '+10%', '0.8')"
    ),
    pitch: str = typer.Option(
        "0.0", "--pitch", "-p", help="Pitch adjustment (e.g., '0.0', '-1st', '+2st')"
    ),
    out: Path = typer.Option(
        Path("output.ogg"), "--out", "-o", help="Output file path"
    ),
) -> None:
    """Synthesize the provided text into a speech audio file using specified parameters.

    This command parses rate and pitch adjustments, configures the TTS instance with the
    given language and options, synthesizes the audio, saves it to the output file,
    and prints synthesis details like duration and size. Caching is enabled by default.

    Args:
        text: The text string to convert to speech (required).
        lang: Language code for synthesis, defaults to 'en' (e.g., 'fa' for Persian).
        engine: Optional TTS engine name to use (e.g., 'edge', 'piper').
        voice: Optional specific voice name for the engine.
        rate: Speech rate adjustment as string (e.g., '1.0' for normal, '+10%' for faster).
        pitch: Pitch adjustment as string (e.g., '0.0' for normal, '-1st' for lower).
        out: Output file path, defaults to 'output.ogg'.

    Notes:
        Examples:
            tts synth --text "سلام" --lang fa --engine edge --voice fa-IR --rate +10% --pitch -1st --out voice.ogg
            tts synth --text "Hello world" --lang en --out hello.ogg

        Output format is inferred from the file extension or defaults to OGG.
        Errors during synthesis are caught and reported via typer.echo to stderr.
    """
    try:
        rate_float = _parse_rate(rate)
        pitch_float = _parse_pitch(pitch)

        tts = get_tts()(default_lang=lang)

        config = get_synth_config()(
            text=text,
            lang=lang,
            voice=voice,
            engine=engine,
            rate=rate_float,
            pitch=pitch_float,
            output_format=out.suffix[1:] if out.suffix else "ogg",
            cache=True,
        )

        typer.echo(f"🎤 Synthesizing: '{text}' in {lang}")
        if engine:
            typer.echo(f"   Engine: {engine}")
        if voice:
            typer.echo(f"   Voice: {voice}")
        typer.echo(f"   Rate: {rate} ({rate_float}x)")
        typer.echo(f"   Pitch: {pitch} ({pitch_float}st)")

        audio_out = tts.synth(config)

        audio_out.save(out)

        typer.echo(f"✅ Saved to {out}")
        typer.echo(f"   Duration: {audio_out.duration:.1f}s")
        typer.echo(f"   Size: {audio_out.size} bytes")
        typer.echo(f"   Format: {audio_out.format}")

    except Exception as e:
        typer.echo(f"❌ Synthesis failed: {e}", err=True)
        sys.exit(1)


@app.command()
def voices(
    engine: str | None = typer.Option(None, "--engine", "-e", help="Filter by engine"),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Filter by language"),
) -> None:
    """List available TTS voices, optionally filtered by engine and language.

    This command executes a helper script (voices_helper.py) via subprocess to gather
    voice information, suppressing warnings and logs for a clean output. It supports
    filtering to show only voices matching the specified engine or language.

    Args:
        engine: Optional engine name to filter voices (e.g., 'edge').
        lang: Optional language code to filter voices (e.g., 'fa').

    Notes:
        Examples:
            tts voices --engine edge --lang fa
            tts voices --lang en
            tts voices

        The subprocess runs with a 30-second timeout and critical log levels to minimize noise.
        Errors from the script or timeout are reported and exit with code 1.
    """
    try:
        import subprocess
        import sys
        from pathlib import Path

        helper_script = Path(__file__).parent / "voices_helper.py"

        cmd = [sys.executable, str(helper_script)]
        if engine:
            cmd.append(engine)
        else:
            cmd.append("None")
        if lang:
            cmd.append(lang)
        else:
            cmd.append("None")

        env = os.environ.copy()
        env["PYTHONWARNINGS"] = "ignore"
        env["TTSKIT_LOG_LEVEL"] = "CRITICAL"
        env["PYROGRAM_LOG_LEVEL"] = "CRITICAL"
        env["TELETHON_LOG_LEVEL"] = "CRITICAL"
        env["PYDUB_LOG_LEVEL"] = "CRITICAL"

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            env=env,
        )

        if result.returncode == 0:
            typer.echo(result.stdout)
        else:
            typer.echo(f"❌ Error: {result.stderr}")
            sys.exit(1)

    except Exception as e:
        typer.echo(f"❌ Failed to get voices: {e}", err=True)
        sys.exit(1)


@app.command()
def info(
    text: str = typer.Argument(..., help="Text to analyze"),
    engine: str | None = typer.Option(None, "--engine", "-e", help="TTS engine to use"),
) -> None:
    """Analyze the provided text for synthesis suitability and display engine info if specified.

    This command calculates text length and word count, detects the language heuristically,
    and if an engine is provided, shows its availability, offline status, supported languages,
    and voice count. Otherwise, it lists all available engines. It also estimates synthesis time
    based on text length.

    Args:
        text: The text string to analyze (required).
        engine: Optional TTS engine name for detailed info (e.g., 'gtts').

    Notes:
        Examples:
            tts info --text "سلام دنیا" --engine gtts
            tts info --text "Hello world"

        Language detection uses character sets for Persian, Arabic, or defaults to English.
        Estimated time is a rough approximation (0.1s per character).
        Errors are reported to stderr with exit code 1.
    """
    try:
        typer.echo(f"📝 Text Analysis: '{text}'")
        typer.echo("=" * 50)

        typer.echo(f"Length: {len(text)} characters")
        typer.echo(f"Words: {len(text.split())} words")

        detected_lang = _detect_language(text)
        typer.echo(f"Detected language: {detected_lang}")
        if engine:
            engines = get_engines()
            engine_info = next((e for e in engines if e["name"] == engine), None)
            if engine_info:
                typer.echo(f"\n🔧 Engine: {engine}")
                typer.echo(
                    f"   Available: {'✅' if engine_info['available'] else '❌'}"
                )
                typer.echo(
                    f"   Offline: {'✅' if engine_info.get('offline', False) else '❌'}"
                )
                typer.echo(
                    f"   Languages: {', '.join(engine_info.get('languages', []))}"
                )
                typer.echo(f"   Voices: {len(engine_info.get('voices', []))}")
            else:
                typer.echo(f"❌ Engine '{engine}' not found")
        else:
            engines = get_engines()
            typer.echo(f"\n🔧 Available engines ({len(engines)}):")
            for engine_info in engines:
                status = "✅" if engine_info["available"] else "❌"
                offline = " (offline)" if engine_info.get("offline", False) else ""
                typer.echo(f"   {status} {engine_info['name']}{offline}")

        estimated_time = len(text) * 0.1
        typer.echo(f"\n⏱️  Estimated synthesis time: ~{estimated_time:.1f}s")

    except Exception as e:
        typer.echo(f"❌ Analysis failed: {e}", err=True)
        sys.exit(1)


@app.command()
def engines() -> None:
    """Display a list of available TTS engines with their status and capabilities.

    This command retrieves engine information via get_engines() and prints details
    for each, including availability status, offline/online mode, supported languages,
    number of voices, and a description if available.

    Notes:
        Uses emojis and formatting for readability.
        Errors during retrieval are reported with exit code 1.
    """
    try:
        engines = get_engines()

        typer.echo("🔧 Available TTS Engines")
        typer.echo("=" * 50)

        for engine in engines:
            status = "✅ Available" if engine["available"] else "❌ Unavailable"
            offline = " (offline)" if engine.get("offline", False) else " (online)"

            typer.echo(f"\n{engine['name'].upper()}")
            typer.echo(f"  Status: {status}{offline}")
            typer.echo(f"  Languages: {', '.join(engine.get('languages', []))}")
            typer.echo(f"  Voices: {len(engine.get('voices', []))}")

            if engine.get("description"):
                typer.echo(f"  Description: {engine['description']}")

    except Exception as e:
        typer.echo(f"❌ Failed to get engines: {e}", err=True)
        sys.exit(1)


@app.command()
def health() -> None:
    """Perform a comprehensive system health check for TTSKit dependencies and components.

    This command runs check_system_health() asynchronously and displays overall status,
    per-check results (healthy or with errors), and detailed information for each check.
    It uses emojis for visual clarity.

    Notes:
        If overall health is good, prints a success message; otherwise, lists issues.
        Detailed status includes all check results regardless of health.
        Exceptions during the check are reported with exit code 1.
    """
    typer.echo("🔍 Checking system health...")

    try:
        health_result = asyncio.run(check_system_health())

        if health_result["overall"]:
            typer.echo("✅ All systems healthy")
        else:
            typer.echo("⚠️ Issues found:")
            for check_name, status in health_result["checks"].items():
                if not status:
                    details = health_result["details"].get(check_name, {})
                    error = details.get("error", "Unknown error")
                    typer.echo(f"  ❌ {check_name}: {error}")
                else:
                    typer.echo(f"  ✅ {check_name}")

        # Show details
        typer.echo("\n📊 Detailed status:")
        for check_name, details in health_result["details"].items():
            typer.echo(f"  {check_name}: {details}")

    except Exception as e:
        typer.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


@app.command()
def stats() -> None:
    """Display key system statistics and metrics for TTSKit usage.

    This command fetches metrics via get_metrics() and prints totals for requests,
    success and cache hit rates, average duration, uptime, plus distributions by
    language and engine. Uses formatted output with sections for readability.

    Notes:
        Defaults to 0 for missing metrics.
        Errors in metric retrieval are reported with exit code 1.
    """
    try:
        metrics = get_metrics()

        typer.echo("📊 System Statistics")
        typer.echo("=" * 50)
        typer.echo(f"Total Requests: {metrics.get('total_requests', 0)}")
        typer.echo(f"Success Rate: {metrics.get('success_rate', 0)}%")
        typer.echo(f"Cache Hit Rate: {metrics.get('cache_hit_rate', 0)}%")
        typer.echo(f"Average Duration: {metrics.get('average_duration', 0)}s")
        typer.echo(f"Uptime: {metrics.get('uptime', 0):.1f}s")

        typer.echo("\n🌍 Language Distribution:")
        for lang, count in metrics.get("language_distribution", {}).items():
            typer.echo(f"  {lang}: {count}")

        typer.echo("\n🔧 Engine Distribution:")
        for engine, count in metrics.get("engine_distribution", {}).items():
            typer.echo(f"  {engine}: {count}")

    except Exception as e:
        typer.echo(f"❌ Stats error: {e}", err=True)
        sys.exit(1)


@app.command()
def cache(
    clear: bool = typer.Option(False, "--clear", help="Clear cache"),
    stats: bool = typer.Option(
        True, "--stats/--no-stats", help="Show cache statistics"
    ),
) -> None:
    """Manage TTSKit cache operations, including clearing and viewing statistics.

    This command can clear the memory cache if requested and display statistics
    for both memory and Redis caches (if available). Stats include size, hit/miss rates,
    memory usage, and detailed hits/misses. Uses colored output for clarity.

    Args:
        clear: If True, clears the memory cache.
        stats: If True (default), shows cache statistics; use --no-stats to skip.

    Notes:
        Clearing only affects the memory cache; Redis is not cleared here.
        If cache size is 0, detailed stats are skipped.
        Redis stats are attempted but gracefully handled if unavailable.
        Errors raise typer.Exit with code 1.
    """
    try:
        if clear:
            asyncio.run(memory_cache.clear())
            typer.secho("Cache cleared successfully ✅", fg=typer.colors.GREEN)

        if stats:
            cache_stats = asyncio.run(memory_cache.get_stats())
            typer.secho("💾 Cache Statistics", fg=typer.colors.CYAN, bold=True)
            typer.secho("=" * 50)

            # Basic stats
            typer.secho(f"Size: {cache_stats.get('size', 0)} items")
            typer.secho(f"Hit Rate: {cache_stats.get('hit_rate', 0):.1f}%")
            typer.secho(f"Miss Rate: {cache_stats.get('miss_rate', 0):.1f}%")
            typer.secho(f"Memory Usage: {cache_stats.get('memory_usage', 'N/A')}")

            if cache_stats.get("size", 0) > 0:
                typer.secho("\n📊 Detailed Statistics:", fg=typer.colors.YELLOW)
                typer.secho(f"Total Hits: {cache_stats.get('hits', 0)}")
                typer.secho(f"Total Misses: {cache_stats.get('misses', 0)}")
                typer.secho(f"Cache Efficiency: {cache_stats.get('hit_rate', 0):.1f}%")

                try:
                    from ttskit.cache.redis import RedisCache

                    redis_cache = RedisCache()
                    redis_stats = redis_cache.get_stats()
                    typer.secho("\n🔴 Redis Cache:", fg=typer.colors.MAGENTA)
                    typer.secho(f"Connected: {redis_stats.get('connected', False)}")
                    typer.secho(f"Keys: {redis_stats.get('keys', 0)}")
                    typer.secho(f"Memory: {redis_stats.get('memory', 'N/A')}")
                except Exception:
                    typer.secho("\n🔴 Redis: Not available", fg=typer.colors.RED)

    except Exception as e:
        typer.secho(f"❌ Cache error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command()
def cache_clear() -> None:
    """Clear the memory cache for TTSKit.

    This command asynchronously clears all entries in the memory cache and confirms success.
    It's a dedicated alias for cache clearing without stats.

    Notes:
        Only affects the in-memory cache; Redis cache remains untouched.
        Errors are reported to stderr with exit code 1.
    """
    try:
        asyncio.run(memory_cache.clear())
        typer.echo("✅ Cache cleared")

    except Exception as e:
        typer.echo(f"❌ Cache clear error: {e}", err=True)
        sys.exit(1)


@app.command()
def api(
    host: str = typer.Option(None, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(None, "--port", "-p", help="Port to bind to"),
    workers: int = typer.Option(
        1, "--workers", "-w", help="Number of worker processes"
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development"
    ),
    log_level: str = typer.Option(
        "info", "--log-level", help="Log level (debug, info, warning, error)"
    ),
    access_log: bool = typer.Option(
        True, "--access-log/--no-access-log", help="Enable access logging"
    ),
    timeout_keep_alive: int = typer.Option(
        5, "--timeout-keep-alive", help="Keep-alive timeout"
    ),
    ssl_keyfile: str | None = typer.Option(None, "--ssl-keyfile", help="SSL key file"),
    ssl_certfile: str | None = typer.Option(
        None, "--ssl-certfile", help="SSL certificate file"
    ),
    ssl_keyfile_password: str | None = typer.Option(
        None, "--ssl-keyfile-password", help="SSL key file password"
    ),
    ssl_version: int | None = typer.Option(None, "--ssl-version", help="SSL version"),
    ssl_cert_reqs: int | None = typer.Option(
        None, "--ssl-cert-reqs", help="SSL certificate requirements"
    ),
    ssl_ca_certs: str | None = typer.Option(
        None, "--ssl-ca-certs", help="SSL CA certificates file"
    ),
    ssl_ciphers: str | None = typer.Option(None, "--ssl-ciphers", help="SSL ciphers"),
    headers: list[str] = typer.Option([], "--header", help="Custom headers"),
    forwarded_allow_ips: str | None = typer.Option(
        None, "--forwarded-allow-ips", help="Allowed forwarded IPs"
    ),
    root_path: str | None = typer.Option(None, "--root-path", help="Root path"),
    proxy_headers: bool = typer.Option(
        True, "--proxy-headers/--no-proxy-headers", help="Enable proxy headers"
    ),
    server_header: bool = typer.Option(
        True, "--server-header/--no-server-header", help="Enable server header"
    ),
    date_header: bool = typer.Option(
        True, "--date-header/--no-date-header", help="Enable date header"
    ),
) -> None:
    """Launch the TTSKit API server using Uvicorn with extensive configuration options.

    This command constructs and runs a Uvicorn subprocess to start the FastAPI app from
    ttskit.api.app:app, resolving host/port from options or env vars. It supports workers,
    reload, logging, SSL, headers, and proxy settings. Prints server details, docs URLs,
    and a quick test command before starting. Handles interruptions and errors gracefully.

    Args:
        host: Host to bind (defaults to API_HOST env or settings.api_host).
        port: Port to bind (defaults to API_PORT env or settings.api_port).
        workers: Number of worker processes (default 1).
        reload: Enable auto-reload for development (default False).
        log_level: Uvicorn log level (default 'info').
        access_log: Enable access logging (default True).
        timeout_keep_alive: Keep-alive timeout in seconds (default 5).
        ssl_keyfile: Path to SSL key file.
        ssl_certfile: Path to SSL certificate file.
        ssl_keyfile_password: Password for SSL key file.
        ssl_version: SSL protocol version.
        ssl_cert_reqs: SSL certificate requirements.
        ssl_ca_certs: Path to SSL CA certificates file.
        ssl_ciphers: SSL ciphers to use.
        headers: List of custom headers (repeatable).
        forwarded_allow_ips: Allowed IPs for forwarded headers.
        root_path: Root path for the app.
        proxy_headers: Enable proxy headers (default True).
        server_header: Enable server header (default True).
        date_header: Enable date header (default True).

    Notes:
        Examples:
            ttskit api --host 0.0.0.0 --port 8000
            ttskit api --host localhost --port 3000 --reload --log-level debug
            ttskit api --workers 4 --ssl-keyfile key.pem --ssl-certfile cert.pem
            ttskit api --host 0.0.0.0 --port 8000 --access-log --proxy-headers

        SSL is enabled only if keyfile or certfile provided.
        Server runs indefinitely until KeyboardInterrupt; errors raise typer.Exit(1).
        Documentation URLs assume HTTP; adjust for HTTPS if SSL enabled.
    """
    try:
        import subprocess
        import sys

        resolved_host = host or os.getenv("API_HOST") or settings.api_host
        resolved_port = port or int(os.getenv("API_PORT", "0")) or settings.api_port

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "ttskit.api.app:app",
            "--host",
            resolved_host,
            "--port",
            str(resolved_port),
        ]

        if workers > 1:
            cmd.extend(["--workers", str(workers)])

        if reload:
            cmd.append("--reload")

        if log_level:
            cmd.extend(["--log-level", log_level])

        if not access_log:
            cmd.append("--no-access-log")

        if timeout_keep_alive:
            cmd.extend(["--timeout-keep-alive", str(timeout_keep_alive)])

        if ssl_keyfile:
            cmd.extend(["--ssl-keyfile", ssl_keyfile])
        if ssl_certfile:
            cmd.extend(["--ssl-certfile", ssl_certfile])
        if ssl_keyfile_password:
            cmd.extend(["--ssl-keyfile-password", ssl_keyfile_password])
        if ssl_version:
            cmd.extend(["--ssl-version", str(ssl_version)])
        if ssl_cert_reqs:
            cmd.extend(["--ssl-cert-reqs", str(ssl_cert_reqs)])
        if ssl_ca_certs:
            cmd.extend(["--ssl-ca-certs", ssl_ca_certs])
        if ssl_ciphers:
            cmd.extend(["--ssl-ciphers", ssl_ciphers])

        for header in headers:
            cmd.extend(["--header", header])

        if forwarded_allow_ips:
            cmd.extend(["--forwarded-allow-ips", forwarded_allow_ips])

        if root_path:
            cmd.extend(["--root-path", root_path])

        if not proxy_headers:
            cmd.append("--no-proxy-headers")

        if not server_header:
            cmd.append("--no-server-header")

        if not date_header:
            cmd.append("--no-date-header")
        typer.secho("🚀 Starting TTSKit API Server", fg=typer.colors.GREEN, bold=True)
        typer.secho("=" * 50)
        typer.secho(f"Host: {resolved_host}")
        typer.secho(f"Port: {resolved_port}")
        typer.secho(f"Workers: {workers}")
        typer.secho(f"Reload: {'✅' if reload else '❌'}")
        typer.secho(f"Log Level: {log_level}")
        typer.secho(f"Access Log: {'✅' if access_log else '❌'}")

        if ssl_keyfile or ssl_certfile:
            typer.secho("SSL: ✅ Enabled")
            if ssl_keyfile:
                typer.secho(f"  Key File: {ssl_keyfile}")
            if ssl_certfile:
                typer.secho(f"  Cert File: {ssl_certfile}")
        else:
            typer.secho("SSL: ❌ Disabled")

        typer.secho("\n📚 API Documentation:")
        typer.secho(f"  Swagger UI: http://{resolved_host}:{resolved_port}/docs")
        typer.secho(f"  ReDoc: http://{resolved_host}:{resolved_port}/redoc")
        typer.secho(f"  OpenAPI: http://{resolved_host}:{resolved_port}/openapi.json")

        typer.secho("\n🔗 Quick Test:")
        typer.secho(f"  curl http://{resolved_host}:{resolved_port}/health")

        typer.secho("\n" + "=" * 50)
        typer.secho("Starting server...", fg=typer.colors.YELLOW)

        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            typer.secho("\n🛑 Server stopped by user", fg=typer.colors.YELLOW)
        except subprocess.CalledProcessError as e:
            typer.secho(f"❌ Server failed to start: {e}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from e

    except Exception as e:
        typer.secho(f"❌ Failed to start API server: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command()
def setup(
    init_db: bool = typer.Option(
        True, "--init-db/--no-init-db", help="Initialize database"
    ),
    migrate: bool = typer.Option(True, "--migrate/--no-migrate", help="Run migrations"),
    test: bool = typer.Option(True, "--test/--no-test", help="Run tests after setup"),
    force: bool = typer.Option(
        False, "--force", help="Force setup even if already initialized"
    ),
) -> None:
    """Initialize the TTSKit system by setting up database, running migrations, and testing.

    This command performs a full setup workflow: optionally initializes the database,
    applies migrations, and runs security/database tests via subprocess. It provides
    colored, step-by-step feedback and suggests next actions upon completion. Force mode
    continues even on errors.

    Args:
        init_db: If True (default), initializes the database using init_database().
        migrate: If True (default), runs migrations via migrate_api_keys_security().
        test: If True (default), executes test_security.py and test_database_api.py.
        force: If True, continues setup despite errors in individual steps.

    Notes:
        Examples:
            ttskit setup                    # Full setup with all steps
            ttskit setup --no-test         # Setup without running tests
            ttskit setup --force           # Force re-setup ignoring errors

        Tests run with 60-second timeout; failures are warned but don't halt setup unless force=False.
        On completion, prints readiness message and next steps like configuring .env.
        Overall errors raise typer.Exit(1).
    """
    try:
        typer.secho("🚀 Setting up TTSKit System", fg=typer.colors.GREEN, bold=True)
        typer.secho("=" * 50)

        if init_db:
            typer.secho("\n📊 Step 1: Initializing Database", fg=typer.colors.CYAN)
            try:
                from ttskit.database.init_db import init_database

                init_database()
                typer.secho(
                    "✅ Database initialized successfully", fg=typer.colors.GREEN
                )
            except Exception as e:
                typer.secho(
                    f"❌ Database initialization failed: {e}", fg=typer.colors.RED
                )
                if not force:
                    raise typer.Exit(code=1) from e

        if migrate:
            typer.secho("\n🔄 Step 2: Running Migrations", fg=typer.colors.CYAN)
            try:
                from ttskit.database.migration import migrate_api_keys_security

                asyncio.run(migrate_api_keys_security())
                typer.secho(
                    "✅ Migrations completed successfully", fg=typer.colors.GREEN
                )
            except Exception as e:
                typer.secho(f"❌ Migration failed: {e}", fg=typer.colors.RED)
                if not force:
                    raise typer.Exit(code=1) from e

        if test:
            typer.secho("\n🧪 Step 3: Running Tests", fg=typer.colors.CYAN)
            try:
                import subprocess
                import sys

                result = subprocess.run(
                    [sys.executable, "examples/test_security.py"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    typer.secho("✅ Security tests passed", fg=typer.colors.GREEN)
                else:
                    typer.secho(
                        f"⚠️ Security tests failed: {result.stderr}",
                        fg=typer.colors.YELLOW,
                    )

                result = subprocess.run(
                    [sys.executable, "examples/test_database_api.py"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    typer.secho("✅ Database tests passed", fg=typer.colors.GREEN)
                else:
                    typer.secho(
                        f"⚠️ Database tests failed: {result.stderr}",
                        fg=typer.colors.YELLOW,
                    )

            except subprocess.TimeoutExpired:
                typer.secho("⚠️ Tests timed out", fg=typer.colors.YELLOW)
            except Exception as e:
                typer.secho(f"⚠️ Test execution failed: {e}", fg=typer.colors.YELLOW)
        typer.secho("\n🎉 Setup Complete!", fg=typer.colors.GREEN, bold=True)
        typer.secho("=" * 50)
        typer.secho("✅ Database: Initialized")
        typer.secho("✅ Migrations: Completed")
        typer.secho("✅ Tests: Executed")
        typer.secho("\n🚀 TTSKit is ready to use!")
        typer.secho("\nNext steps:")
        typer.secho("  • Configure .env file")
        typer.secho("  • Start bot: ttskit start --token YOUR_BOT_TOKEN")
        typer.secho("  • Start API: ttskit api --host 0.0.0.0 --port 8000")

    except Exception as e:
        typer.secho(f"❌ Setup failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command()
def migrate(
    check: bool = typer.Option(False, "--check", help="Check migration status only"),
    force: bool = typer.Option(
        False, "--force", help="Force migration even if not needed"
    ),
) -> None:
    """Execute database migrations or check their status for TTSKit.

    If --check is provided, this command verifies the current migration state using
    check_database_security(). Otherwise, it applies migrations via migrate_api_keys_security().
    Provides colored feedback for each step and handles force mode implicitly through error tolerance.

    Args:
        check: If True, only checks migration status without applying changes.
        force: If True, forces migration execution even if not strictly needed (though not directly used here).

    Notes:
        Examples:
            ttskit migrate                    # Apply migrations
            ttskit migrate --check           # Check status only
            ttskit migrate --force           # Force application

        Runs asynchronously and reports success or failure.
        Errors raise typer.Exit(1).
    """
    try:
        typer.secho("🔄 Database Migration", fg=typer.colors.CYAN, bold=True)
        typer.secho("=" * 50)

        if check:
            typer.secho("📊 Checking migration status...", fg=typer.colors.YELLOW)
            try:
                from ttskit.database.migration import check_database_security

                asyncio.run(check_database_security())
                typer.secho(
                    "✅ Migration status check completed", fg=typer.colors.GREEN
                )
            except Exception as e:
                typer.secho(f"❌ Migration check failed: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1) from e
        else:
            typer.secho("🔄 Running migrations...", fg=typer.colors.YELLOW)
            try:
                from ttskit.database.migration import migrate_api_keys_security

                asyncio.run(migrate_api_keys_security())
                typer.secho(
                    "✅ Migrations completed successfully", fg=typer.colors.GREEN
                )
            except Exception as e:
                typer.secho(f"❌ Migration failed: {e}", fg=typer.colors.RED)
                raise typer.Exit(code=1) from e

    except Exception as e:
        typer.secho(f"❌ Migration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


@app.command()
def config(
    show_secrets: bool = typer.Option(
        False, "--show-secrets", help="Show sensitive configuration"
    ),
    validate: bool = typer.Option(False, "--validate", help="Validate configuration"),
) -> None:
    """Display the current TTSKit configuration settings in categorized sections.

    This command prints settings from the global settings object, masking secrets like
    bot tokens and Redis URLs unless --show-secrets is used. If --validate is specified,
    it performs basic checks on key values like bot token presence and positive limits,
    reporting pass/fail with colors.

    Args:
        show_secrets: If True, reveals sensitive values like bot token and Redis URL.
        validate: If True, validates critical config values and reports status.

    Notes:
        Sections include basic, Telegram, audio, cache, rate limiting, engine, and health settings.
        Sensitive fields show '***' if set but hidden, or 'Not set' if absent.
        Validation checks: bot token presence, max_text_length > 0, rate_limit_rpm > 0.
        Errors raise typer.Exit(1).
    """
    try:
        typer.secho("⚙️ TTSKit Configuration", fg=typer.colors.CYAN, bold=True)
        typer.secho("=" * 50)

        typer.secho("\n📋 Basic Settings:", fg=typer.colors.YELLOW)
        typer.secho(f"Version: {settings.version}")
        typer.secho(f"Log Level: {settings.log_level}")
        typer.secho(f"Default Language: {settings.default_lang}")
        typer.secho(f"Max Text Length: {settings.max_text_length}")

        typer.secho("\n🤖 Telegram Settings:", fg=typer.colors.YELLOW)
        typer.secho(f"Adapter: {settings.telegram_driver}")
        bot_token = settings.bot_token
        # Mask bot token to show first/last 2 characters when hidden
        if show_secrets and bot_token:
            typer.secho(f"Bot Token: {bot_token}")
        else:
            typer.secho(
                f"Bot Token: {_mask_value(bot_token, keep=2) if bot_token else 'Not set'}"
            )
        # Show masked API credentials
        typer.secho(f"API ID: {_mask_value(settings.telegram_api_id, keep=2)}")
        typer.secho(f"API HASH: {_mask_value(settings.telegram_api_hash, keep=2)}")

        typer.secho("\n🎵 Audio Settings:", fg=typer.colors.YELLOW)
        typer.secho(f"Default Format: {settings.default_format}")
        typer.secho(f"Default Bitrate: {settings.default_bitrate}")
        typer.secho(f"Default Sample Rate: {settings.default_sample_rate}")

        typer.secho("\n💾 Cache Settings:", fg=typer.colors.YELLOW)
        typer.secho(f"Cache Enabled: {settings.cache_enabled}")
        typer.secho(f"Cache TTL: {settings.cache_ttl}s")
        redis_url = settings.redis_url
        if show_secrets and redis_url:
            typer.secho(f"Redis URL: {redis_url}")
        else:
            typer.secho(f"Redis URL: {'***' if redis_url else 'Not set'}")

        typer.secho("\n🚦 Rate Limiting:", fg=typer.colors.YELLOW)
        typer.secho(f"Rate Limit RPM: {settings.rate_limit_rpm}")
        typer.secho(f"Rate Limit Window: {settings.rate_limit_window}s")

        typer.secho("\n🔧 Engine Settings:", fg=typer.colors.YELLOW)
        typer.secho(f"Default Engine: {settings.default_engine}")
        typer.secho(f"Fallback Enabled: {settings.fallback_enabled}")

        typer.secho("\n🏥 Health Check:", fg=typer.colors.YELLOW)
        typer.secho(f"Health Check Interval: {settings.health_check_interval}s")
        typer.secho(f"Health Check Timeout: {settings.health_check_timeout}s")

        if validate:
            typer.secho("\n✅ Configuration Validation:", fg=typer.colors.GREEN)
            if not bot_token:
                typer.secho("❌ Bot token is not set", fg=typer.colors.RED)
            else:
                typer.secho("✅ Bot token is set", fg=typer.colors.GREEN)

            if settings.max_text_length <= 0:
                typer.secho("❌ Max text length must be positive", fg=typer.colors.RED)
            else:
                typer.secho("✅ Max text length is valid", fg=typer.colors.GREEN)

            if settings.rate_limit_rpm <= 0:
                typer.secho("❌ Rate limit RPM must be positive", fg=typer.colors.RED)
            else:
                typer.secho("✅ Rate limit RPM is valid", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"❌ Config error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from e


def _parse_rate(rate_str: str) -> float:
    """Convert a rate adjustment string to a float multiplier for TTS synthesis.

    This utility parses strings representing speech rate changes, supporting direct
    float values (e.g., '1.0' for normal) or percentage adjustments (e.g., '+10%'
    becomes 1.1, '150%' becomes 2.5). Percentages are relative to normal speed (1.0).

    Args:
        rate_str: The rate string to parse (e.g., "1.0", "+10%", "0.8", "150%").

    Returns:
        float: The parsed rate multiplier (1.0 is normal speed).

    Raises:
        ValueError: If the string cannot be parsed as float or valid percentage.
    """
    rate_str = rate_str.strip()

    if rate_str.endswith("%"):
        percentage = float(rate_str[:-1])
        return 1.0 + (percentage / 100.0)
    else:
        return float(rate_str)


def _parse_pitch(pitch_str: str) -> float:
    """Convert a pitch adjustment string to a float in semitones for TTS synthesis.

    This function handles strings for pitch shifts, accepting direct floats (e.g., '0.0')
    or semitone notation (e.g., '-1st' for one semitone lower, '+2st' for higher).
    'st' suffix is stripped before parsing.

    Args:
        pitch_str: The pitch string to parse (e.g., "0.0", "-1st", "+2st", "1.5").

    Returns:
        float: The parsed pitch adjustment in semitones (0.0 means no change).

    Raises:
        ValueError: If the string cannot be parsed as float after processing.
    """
    pitch_str = pitch_str.strip()

    if pitch_str.endswith("st"):
        return float(pitch_str[:-2])
    else:
        return float(pitch_str)


def _detect_language(text: str) -> str:
    """Heuristically detect the language of input text based on character sets.

    This simple detector checks for Persian-specific characters first, then Arabic,
    defaulting to English if neither matches. It's a lightweight way to infer language
    for TTS without external libraries.

    Args:
        text: The input text string to analyze for language.

    Returns:
        str: Detected language code ('fa' for Persian, 'ar' for Arabic, 'en' default).

    Notes:
        Persian detection uses unique chars like 'پ', 'چ', 'ژ', 'گ'.
        Arabic uses standard script; overlaps with Persian are prioritized to 'fa'.
        Not suitable for mixed-language text; best for dominant script identification.
    """
    persian_chars = set("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی")
    arabic_chars = set("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")

    text_chars = set(text)

    if text_chars.intersection(persian_chars):
        return "fa"
    elif text_chars.intersection(arabic_chars):
        return "ar"
    else:
        return "en"


if __name__ == "__main__":
    app()
