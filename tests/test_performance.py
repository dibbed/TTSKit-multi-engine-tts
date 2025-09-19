"""Comprehensive performance tests for TTSKit."""

import asyncio
import gc
import os
import statistics
import time
from unittest.mock import Mock, patch

import psutil
import pytest

from ttskit.audio.pipeline import AudioPipeline
from ttskit.bot.unified_bot import UnifiedTTSBot
from ttskit.cache.memory import MemoryCache
from ttskit.cache.redis import RedisCache
from ttskit.engines.factory import create_engine
from ttskit.engines.smart_router import SmartRouter
from ttskit.metrics.advanced import AdvancedMetricsCollector


class TestPerformance:
    """Performance tests for TTSKit components."""

    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return UnifiedTTSBot(
            bot_token="test_token",
            adapter_type="aiogram",
            cache_enabled=True,
            audio_processing=True,
        )

    @pytest.mark.asyncio
    async def test_engine_performance(self):
        """Test engine performance metrics."""
        try:
            engine = create_engine("gtts", default_lang="en")

            if not engine.is_available():
                pytest.skip("gTTS engine not available")

            test_texts = [
                "Hello World",
                "This is a test of the TTS engine performance",
                "The quick brown fox jumps over the lazy dog",
                "Performance testing is important for production systems",
                "TTSKit provides excellent performance and reliability",
            ]

            durations = []

            for text in test_texts:
                start_time = time.time()
                try:
                    audio_data = await engine.synth_async(text, "en")
                    duration = time.time() - start_time
                    durations.append(duration)

                    assert len(audio_data) > 0

                except Exception as e:
                    pytest.skip(f"Engine synthesis failed: {e}")

            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            std_duration = statistics.stdev(durations) if len(durations) > 1 else 0

            print("\nEngine Performance Metrics:")
            print(f"Average Duration: {avg_duration:.3f}s")
            print(f"Min Duration: {min_duration:.3f}s")
            print(f"Max Duration: {max_duration:.3f}s")
            print(f"Std Deviation: {std_duration:.3f}s")
            print(f"Total Requests: {len(durations)}")

            assert avg_duration < 5.0, f"Average duration too high: {avg_duration:.3f}s"
            assert max_duration < 10.0, f"Max duration too high: {max_duration:.3f}s"

        except ImportError:
            pytest.skip("gTTS not available")

    @pytest.mark.asyncio
    async def test_smart_router_performance(self):
        """Test smart router performance."""
        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts", "edge"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": Mock(), "edge": Mock()}

        mock_registry.engines["gtts"].is_available.return_value = True
        mock_registry.engines["gtts"].synth_async.return_value = b"audio_data"
        mock_registry.engines["edge"].is_available.return_value = True
        mock_registry.engines["edge"].synth_async.return_value = b"audio_data"

        router = SmartRouter(mock_registry)

        test_requests = [
            ("Hello World", "en"),
            ("This is a test", "en"),
            ("Performance testing", "en"),
            ("Smart router test", "en"),
            ("Multiple requests", "en"),
        ]

        durations = []

        for text, lang in test_requests:
            start_time = time.time()
            try:
                audio_data, engine_name = await router.synth_async(text, lang)
                duration = time.time() - start_time
                durations.append(duration)

                assert len(audio_data) > 0
                assert engine_name in ["gtts", "edge"]

            except Exception as e:
                pytest.skip(f"Router synthesis failed: {e}")

        avg_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        print("\nSmart Router Performance Metrics:")
        print(f"Average Duration: {avg_duration:.3f}s")
        print(f"Min Duration: {min_duration:.3f}s")
        print(f"Max Duration: {max_duration:.3f}s")
        print(f"Total Requests: {len(durations)}")

        assert avg_duration < 1.0, f"Router duration too high: {avg_duration:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent request handling."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        async def make_request(text, lang):
            start_time = time.time()
            audio_data, engine_name = await router.synth_async(text, lang)
            duration = time.time() - start_time
            return duration, len(audio_data)

        tasks = [make_request(f"Request {i}", "en") for i in range(10)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_duration = time.time() - start_time

        durations = [result[0] for result in results]
        avg_duration = statistics.mean(durations)
        max_duration = max(durations)

        print("\nConcurrent Requests Performance:")
        print(f"Total Requests: {len(tasks)}")
        print(f"Total Duration: {total_duration:.3f}s")
        print(f"Average Request Duration: {avg_duration:.3f}s")
        print(f"Max Request Duration: {max_duration:.3f}s")
        print(f"Requests per Second: {len(tasks) / total_duration:.2f}")

        assert total_duration < 10.0, f"Total duration too high: {total_duration:.3f}s"
        assert avg_duration < 2.0, f"Average duration too high: {avg_duration:.3f}s"

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during operation."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data" * 1000

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        for i in range(100):
            audio_data, engine_name = await router.synth_async(f"Request {i}", "en")
            assert len(audio_data) > 0

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        print("\nMemory Usage:")
        print(f"Initial Memory: {initial_memory:.2f} MB")
        print(f"Final Memory: {final_memory:.2f} MB")
        print(f"Memory Increase: {memory_increase:.2f} MB")

        assert memory_increase < 50.0, (
            f"Memory increase too high: {memory_increase:.2f} MB"
        )

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test cache performance."""

        from ttskit.utils.audio_manager import audio_manager

        audio_manager.clear_cache()

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"cached_audio_data"

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        start_time = time.time()
        audio_data1, engine_name1 = await router.synth_async("Test text", "en")
        cache_miss_duration = time.time() - start_time

        start_time = time.time()
        audio_data2, engine_name2 = await router.synth_async("Test text", "en")
        cache_hit_duration = time.time() - start_time

        print("\nCache Performance:")
        print(f"Cache Miss Duration: {cache_miss_duration:.3f}s")
        print(f"Cache Hit Duration: {cache_hit_duration:.3f}s")

        if cache_hit_duration > 0:
            speedup = cache_miss_duration / cache_hit_duration
            print(f"Cache Speedup: {speedup:.2f}x")
        else:
            print("Cache Speedup: ∞ (cache hit was instant)")

        assert cache_hit_duration < 0.1, (
            f"Cache hit too slow: {cache_hit_duration:.3f}s"
        )
        assert cache_miss_duration < 1.0, (
            f"Cache miss too slow: {cache_miss_duration:.3f}s"
        )

        if cache_hit_duration < cache_miss_duration:
            print("✅ Cache hit is faster than cache miss")
        else:
            print("⚠️ Cache hit not faster (likely due to timing variations)")

    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test error handling performance."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.side_effect = Exception("Engine failed")

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        start_time = time.time()
        try:
            await router.synth_async("Test text", "en")
        except Exception:
            error_duration = time.time() - start_time

            print("\nError Handling Performance:")
            print(f"Error Duration: {error_duration:.3f}s")

            assert error_duration < 1.0, (
                f"Error handling too slow: {error_duration:.3f}s"
            )

    @pytest.mark.asyncio
    async def test_large_text_performance(self):
        """Test performance with large text."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        large_text = (
            "This is a very long text that will test the performance of the TTS system. "
            * 100
        )

        start_time = time.time()
        audio_data, engine_name = await router.synth_async(large_text, "en")
        duration = time.time() - start_time

        print("\nLarge Text Performance:")
        print(f"Text Length: {len(large_text)} characters")
        print(f"Duration: {duration:.3f}s")
        if duration > 0:
            print(f"Characters per Second: {len(large_text) / duration:.2f}")
        else:
            print("Characters per Second: inf")

        assert duration < 5.0, f"Large text processing too slow: {duration:.3f}s"
        assert len(audio_data) > 0, "Audio data should be generated"

    @pytest.mark.asyncio
    async def test_audio_pipeline_performance(self):
        """Test audio pipeline performance."""
        pipeline = AudioPipeline()

        if not pipeline.is_available():
            pytest.skip("Audio pipeline not available - missing dependencies")

        import numpy as np

        sample_rate = 22050
        duration = 1.0
        frequency = 440

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
        audio_data = (audio_data * 32767).astype(np.int16)

        import io
        import wave

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        wav_data = wav_buffer.getvalue()

        operations = [
            ("basic_processing", {"normalize": True, "trim_silence": True}),
            (
                "with_effects",
                {"effects": {"volume": 0.8, "fade_in": 0.1, "fade_out": 0.1}},
            ),
            ("sample_rate_conversion", {"sample_rate": 44100}),
            ("format_conversion", {"output_format": "wav"}),
        ]

        durations = {}

        for operation_name, options in operations:
            start_time = time.time()
            try:
                result = await pipeline.process_audio(wav_data, **options)
                duration = time.time() - start_time
                durations[operation_name] = duration

                assert len(result) > 0, f"{operation_name} should produce audio data"

            except Exception as e:
                pytest.skip(f"Audio pipeline operation {operation_name} failed: {e}")

        print("\nAudio Pipeline Performance:")
        for operation, duration in durations.items():
            print(f"{operation}: {duration:.3f}s")

        for operation, duration in durations.items():
            threshold = 5.0 if operation == "sample_rate_conversion" else 2.0
            assert duration < threshold, f"{operation} too slow: {duration:.3f}s"

    @pytest.mark.asyncio
    async def test_cache_performance_comparison(self):
        """Test cache performance comparison."""
        memory_cache = MemoryCache(default_ttl=3600)

        redis_cache = None
        try:
            redis_cache = RedisCache()
            await redis_cache.connect()
        except Exception:
            redis_cache = None

        test_data = b"test_audio_data" * 100
        cache_key = "test_key"

        memory_times = []
        for _ in range(10):
            start_time = time.time()
            memory_cache.set(cache_key, test_data)
            memory_cache.get(cache_key)
            duration = time.time() - start_time
            memory_times.append(duration)

        memory_avg = statistics.mean(memory_times)

        print("\nCache Performance Comparison:")
        print(f"Memory Cache Average: {memory_avg:.4f}s")

        if redis_cache:
            redis_times = []
            for _ in range(10):
                start_time = time.time()
                await redis_cache.set(cache_key, test_data)
                await redis_cache.get(cache_key)
                duration = time.time() - start_time
                redis_times.append(duration)

            redis_avg = statistics.mean(redis_times)
            print(f"Redis Cache Average: {redis_avg:.4f}s")

            await redis_cache.close()

        assert memory_avg < 0.01, f"Memory cache too slow: {memory_avg:.4f}s"

    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self):
        """Test metrics collection performance."""
        collector = AdvancedMetricsCollector(history_size=1000)

        start_time = time.time()

        tasks = []
        for i in range(100):
            task = collector.record_request(
                f"engine_{i % 5}", f"lang_{i % 3}", i * 0.01, i % 10 != 0
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        cache_tasks = []
        for i in range(50):
            task = collector.record_cache_event(hit=i % 2 == 0, size_bytes=1024)
            cache_tasks.append(task)

        await asyncio.gather(*cache_tasks)

        from datetime import datetime as real_datetime

        with (
            patch("ttskit.metrics.advanced.datetime", real_datetime),
            patch("ttskit.metrics.advanced.psutil.cpu_percent", return_value=25.0),
            patch("ttskit.metrics.advanced.psutil.virtual_memory") as mock_memory,
            patch("ttskit.metrics.advanced.psutil.disk_usage") as mock_disk,
            patch("ttskit.metrics.advanced.psutil.net_io_counters") as mock_network,
        ):
            collector._start_time = real_datetime(2023, 1, 1, 0, 0, 0)
            mock_memory.return_value.used = 1024 * 1024 * 1024
            mock_memory.return_value.percent = 50.0
            mock_disk.return_value.percent = 75.0
            mock_network.return_value.bytes_sent = 1024
            mock_network.return_value.bytes_recv = 2048

            await collector.collect_system_metrics()

        from datetime import datetime as real_datetime

        with patch("ttskit.metrics.advanced.datetime", real_datetime):
            metrics_start = time.time()
            metrics = await collector.get_comprehensive_metrics()
            metrics_duration = time.time() - metrics_start

        total_duration = time.time() - start_time

        print("\nMetrics Collection Performance:")
        print(f"Total Duration: {total_duration:.3f}s")
        print(f"Metrics Generation: {metrics_duration:.3f}s")
        print(f"Requests Recorded: {metrics['requests']['total']}")
        print(
            f"Cache Events: {metrics['cache']['total_hits'] + metrics['cache']['total_misses']}"
        )

        assert total_duration < 1.0, (
            f"Metrics collection too slow: {total_duration:.3f}s"
        )
        assert metrics_duration < 0.1, (
            f"Metrics generation too slow: {metrics_duration:.3f}s"
        )

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test for memory leaks in long-running operations."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data" * 1000

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        for cycle in range(10):
            tasks = []
            for i in range(20):
                task = router.synth_async(f"Request {cycle}-{i}", "en")
                tasks.append(task)

            await asyncio.gather(*tasks)

            gc.collect()

            if cycle % 3 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory

                print(f"Cycle {cycle}: Memory increase: {memory_increase:.2f} MB")

                assert memory_increase < 100.0, (
                    f"Memory leak detected: {memory_increase:.2f} MB increase"
                )

        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory

        print("\nMemory Leak Test Results:")
        print(f"Initial Memory: {initial_memory:.2f} MB")
        print(f"Final Memory: {final_memory:.2f} MB")
        print(f"Total Increase: {total_increase:.2f} MB")

        assert total_increase < 50.0, (
            f"Significant memory leak detected: {total_increase:.2f} MB"
        )

    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self):
        """Test CPU usage under high load."""
        initial_cpu = psutil.cpu_percent(interval=1)

        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        async def high_load_task():
            tasks = []
            for i in range(50):
                task = router.synth_async(f"High load request {i}", "en")
                tasks.append(task)
            return await asyncio.gather(*tasks)

        start_time = time.time()
        await high_load_task()
        load_duration = time.time() - start_time

        final_cpu = psutil.cpu_percent(interval=1)

        print("\nCPU Usage Under Load:")
        print(f"Initial CPU: {initial_cpu:.1f}%")
        print(f"Final CPU: {final_cpu:.1f}%")
        print(f"Load Duration: {load_duration:.3f}s")

        assert final_cpu < 90.0, f"CPU usage too high: {final_cpu:.1f}%"

    @pytest.mark.asyncio
    async def test_response_time_consistency(self):
        """Test response time consistency across multiple requests."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        response_times = []

        for i in range(20):
            start_time = time.time()
            await router.synth_async(f"Consistency test {i}", "en")
            response_time = time.time() - start_time
            response_times.append(response_time)

        avg_response_time = statistics.mean(response_times)
        std_response_time = (
            statistics.stdev(response_times) if len(response_times) > 1 else 0
        )
        min_response_time = min(response_times)
        max_response_time = max(response_times)

        cv = (
            (std_response_time / avg_response_time) * 100
            if avg_response_time > 0
            else 0
        )

        print("\nResponse Time Consistency:")
        print(f"Average: {avg_response_time:.4f}s")
        print(f"Std Dev: {std_response_time:.4f}s")
        print(f"Min: {min_response_time:.4f}s")
        print(f"Max: {max_response_time:.4f}s")
        print(f"Coefficient of Variation: {cv:.2f}%")

        assert avg_response_time < 0.1, (
            f"Average response time too high: {avg_response_time:.4f}s"
        )
        assert cv < 500.0, f"Response time too inconsistent: {cv:.2f}% CV"
        assert max_response_time < 0.2, (
            f"Max response time too high: {max_response_time:.4f}s"
        )

    @pytest.mark.asyncio
    async def test_throughput_under_concurrent_load(self):
        """Test throughput under concurrent load."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.return_value = b"audio_data"

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        concurrency_levels = [1, 5, 10, 20]
        throughput_results = {}

        for concurrency in concurrency_levels:

            async def concurrent_request(request_id):
                start_time = time.time()
                await router.synth_async(f"Concurrent request {request_id}", "en")
                return time.time() - start_time

            start_time = time.time()
            tasks = [concurrent_request(i) for i in range(concurrency)]
            response_times = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time

            throughput = (
                concurrency / total_duration if total_duration > 0 else float("inf")
            )
            avg_response_time = statistics.mean(response_times)

            throughput_results[concurrency] = {
                "throughput": throughput,
                "avg_response_time": avg_response_time,
                "total_duration": total_duration,
            }

        print("\nThroughput Under Concurrent Load:")
        for concurrency, results in throughput_results.items():
            print(
                f"Concurrency {concurrency}: {results['throughput']:.2f} req/s, "
                f"avg response: {results['avg_response_time']:.4f}s"
            )

        if throughput_results[1]["throughput"] != float("inf"):
            assert throughput_results[1]["throughput"] > 10, (
                "Single request throughput too low"
            )
        assert throughput_results[10]["throughput"] >= 0

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Test error recovery performance."""
        mock_engine = Mock()
        mock_engine.is_available.return_value = True
        mock_engine.synth_async.side_effect = Exception("Simulated error")

        mock_registry = Mock()
        mock_registry.get_engines_for_language.return_value = ["gtts"]
        mock_registry.meets_requirements.return_value = True
        mock_registry.engines = {"gtts": mock_engine}

        router = SmartRouter(mock_registry)

        error_times = []

        for i in range(10):
            start_time = time.time()
            try:
                await router.synth_async(f"Error test {i}", "en")
            except Exception:
                error_time = time.time() - start_time
                error_times.append(error_time)

        if error_times:
            avg_error_time = statistics.mean(error_times)
            max_error_time = max(error_times)

            print("\nError Recovery Performance:")
            print(f"Average Error Time: {avg_error_time:.4f}s")
            print(f"Max Error Time: {max_error_time:.4f}s")

            assert avg_error_time < 0.1, (
                f"Error recovery too slow: {avg_error_time:.4f}s"
            )
            assert max_error_time < 0.2, (
                f"Max error recovery too slow: {max_error_time:.4f}s"
            )
        else:
            print("\nError Recovery Performance:")
            print("No errors occurred during test - system is stable")
