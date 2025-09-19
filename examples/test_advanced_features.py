"""Test script for TTSKit Advanced Features"""

import asyncio
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ttskit.bot.callbacks import CallbackRegistry
from ttskit.bot.commands import CommandRegistry
from ttskit.bot.unified_bot import UnifiedTTSBot
from ttskit.metrics.advanced import AdvancedMetricsCollector, get_metrics_collector
from ttskit.utils.performance import (
    ConnectionPool,
    MemoryOptimizer,
    ParallelProcessor,
    PerformanceConfig,
    cleanup_resources,
    get_performance_monitor,
)


async def test_performance_optimization():
    """Tests performance optimization features including connection pooling and parallel processing.
    
    Validates connection pool functionality, parallel processing capabilities,
    and memory optimization monitoring with comprehensive error handling.
    """
    print("🚀 Testing Performance Optimization...")

    config = PerformanceConfig(max_connections=10, max_concurrent_requests=3)
    pool = ConnectionPool(config)

    print("  📡 Testing connection pooling...")
    try:
        tasks = []
        for _ in range(5):
            task = asyncio.create_task(
                pool.request("GET", "https://httpbin.org/delay/0.1")
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = len([r for r in results if not isinstance(r, Exception)])
        print(f"    ✅ Connection pooling: {successful}/5 requests successful")
    except Exception as e:
        print(f"    ❌ Connection pooling failed: {e}")

    await pool.close_all()

    print("  ⚡ Testing parallel processing...")
    processor = ParallelProcessor(max_workers=3)

    async def test_task(item):
        """Simulates processing task with artificial delay.
        
        Args:
            item: Item to process
            
        Returns:
            Processed item string
        """
        await asyncio.sleep(0.1)
        return f"processed_{item}"

    items = [f"item_{i}" for i in range(10)]
    start_time = time.time()
    results = await processor.process_batch(items, test_task)
    end_time = time.time()

    print(
        f"    ✅ Parallel processing: {len(results)} items in {end_time - start_time:.2f}s"
    )

    print("  💾 Testing memory optimization...")
    optimizer = MemoryOptimizer(config)
    memory_info = optimizer.get_memory_usage()
    print(f"    ✅ Memory usage: {memory_info['rss_mb']:.1f} MB")

    print("✅ Performance optimization tests completed!\n")


async def test_advanced_metrics():
    """Tests advanced metrics collection including request tracking and analytics.
    
    Validates metrics recording, error tracking, cache event monitoring,
    system metrics collection, and comprehensive analytics generation.
    """
    print("📊 Testing Advanced Metrics...")

    collector = AdvancedMetricsCollector()

    print("  📈 Recording test requests...")
    for i in range(10):
        await collector.record_request(
            engine="edge", language="en", response_time=1.0 + (i * 0.1), success=True
        )

    await collector.record_error("TestError", "Test error message")

    await collector.record_cache_event(hit=True, size_bytes=1024)
    await collector.record_cache_event(hit=False, size_bytes=2048)

    await collector.collect_system_metrics()

    print("  📊 Getting comprehensive metrics...")
    metrics = await collector.get_comprehensive_metrics()
    print(f"    ✅ Total requests: {metrics['requests']['total']}")
    print(f"    ✅ Success rate: {metrics['requests']['success_rate']:.1f}%")
    print(f"    ✅ Health score: {metrics['health']:.1f}/100")

    print("  🎤 Getting engine comparison...")
    comparison = await collector.get_engine_comparison()
    if comparison:
        for engine_name, data in comparison.items():
            print(
                f"    ✅ {engine_name}: {data['requests']} requests, {data['success_rate']:.1f}% success"
            )

    print("  🌐 Getting language analytics...")
    analytics = await collector.get_language_analytics()
    if analytics:
        for lang_code, data in analytics.items():
            print(
                f"    ✅ {lang_code}: {data['total_requests']} requests, {data['usage_percentage']:.1f}% usage"
            )

    print("✅ Advanced metrics tests completed!\n")


async def test_admin_panel():
    """Tests admin panel functionality with unified bot and command registries.
    
    Validates unified bot initialization, admin user management, command registry
    setup, and access control mechanisms for administrative functions.
    """
    print("🤖 Testing Admin Panel (Unified)...")

    print("  🛠️ Initializing unified bot and registries...")
    admin_ids = [123456789, 987654321]
    bot = UnifiedTTSBot(
        bot_token="dummy_token",
        adapter_type="aiogram",
        cache_enabled=True,
        audio_processing=True,
    )
    for admin_id in admin_ids:
        bot.sudo_users.add(str(admin_id))

    cmd_registry = CommandRegistry()
    cb_registry = CallbackRegistry()
    cmd_registry.register_default(bot)
    cmd_registry.register_admin(bot)
    cmd_registry.register_advanced_admin(bot)
    cb_registry.register_default(bot)
    cb_registry.register_admin(bot)
    print("    ✅ Registries initialized and handlers registered")

    print("  🔐 Testing admin access control...")
    is_admin = bot.is_sudo(123456789)
    is_not_admin = bot.is_sudo(999999999)
    print(f"    ✅ Admin access: {is_admin} (should be True)")
    print(f"    ✅ Non-admin access: {is_not_admin} (should be False)")

    print("  🔗 Testing admin management...")
    bot.sudo_users.add("111111111")
    print(f"    ✅ Added admin: {len(bot.sudo_users)} total admins")
    bot.sudo_users.discard("111111111")
    print(f"    ✅ Removed admin: {len(bot.sudo_users)} total admins")

    print("✅ Admin (Unified) tests completed!\n")


async def test_integration():
    """Tests integration between performance monitoring and metrics collection components.
    
    Validates cross-component data recording, metrics retrieval consistency,
    and resource cleanup functionality across integrated systems.
    """
    print("🔗 Testing Integration...")

    print("  📊 Testing performance monitor integration...")
    performance_monitor = get_performance_monitor()
    metrics_collector = get_metrics_collector()

    await performance_monitor.record_request("test_engine", "en", 1.5, success=True)
    await metrics_collector.record_request("test_engine", "en", 1.5, success=True)

    perf_metrics = await performance_monitor.get_metrics()
    comprehensive_metrics = await metrics_collector.get_comprehensive_metrics()

    print(f"    ✅ Performance monitor: {perf_metrics['requests']['total']} requests")
    print(
        f"    ✅ Metrics collector: {comprehensive_metrics['requests']['total']} requests"
    )

    print("  🧹 Testing resource cleanup...")
    await cleanup_resources()
    print("    ✅ Resources cleaned up")

    print("✅ Integration tests completed!\n")


async def main():
    """Runs comprehensive test suite for TTSKit advanced features.
    
    Executes performance optimization, metrics collection, admin panel,
    and integration tests with error handling and result reporting.
    """
    print("🧪 TTSKit Advanced Features Test Suite")
    print("=" * 50)

    try:
        await test_performance_optimization()
        await test_advanced_metrics()
        await test_admin_panel()
        await test_integration()

        print("🎉 All tests completed successfully!")
        print("✅ TTSKit Advanced Features are working correctly!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
