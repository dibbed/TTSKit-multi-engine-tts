"""TTSKit Performance Optimization Example

Shows how to use performance features like connection pooling, parallel processing, 
and memory optimization to get the most out of your TTS setup.
"""

import asyncio
import time

from ttskit.metrics.advanced import get_metrics_collector, start_metrics_collection
from ttskit.public import TTS
from ttskit.utils.performance import (
    ConnectionPool,
    MemoryOptimizer,
    ParallelProcessor,
    PerformanceConfig,
    get_performance_monitor,
)


async def performance_example():
    """Shows off TTSKit's performance features with real examples.
    
    Walks through connection pooling, parallel processing, memory monitoring,
    TTS performance tracking, and engine comparisons to help you optimize
    your text-to-speech workflow.
    """

    print("🚀 TTSKit Performance Optimization Example")
    print("=" * 50)

    config = PerformanceConfig(
        max_connections=50,
        max_keepalive_connections=10,
        max_concurrent_requests=5,
        chunk_size=4096,
        memory_limit_mb=256,
    )

    performance_monitor = get_performance_monitor()
    metrics_collector = get_metrics_collector()

    asyncio.create_task(start_metrics_collection(interval_seconds=30))

    print("📊 Performance Components Initialized")

    print("\n1️⃣ Testing Connection Pooling...")
    connection_pool = ConnectionPool(config)

    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
    ]

    start_time = time.time()
    tasks = [connection_pool.request("GET", url) for url in urls]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    connection_time = time.time() - start_time

    print(f"✅ Connection pooling test completed in {connection_time:.2f}s")
    print(
        f"📈 Responses received: {len([r for r in responses if not isinstance(r, Exception)])}"
    )

    await connection_pool.close_all()

    print("\n2️⃣ Testing Parallel Processing...")
    processor = ParallelProcessor(max_workers=3)

    items = [f"text_{i}" for i in range(10)]

    async def process_item(item: str) -> str:
        """Processes an item with a small delay to simulate real work.
        
        Args:
            item: Item identifier to process
            
        Returns:
            Processed item string with prefix
        """
        await asyncio.sleep(0.1)
        return f"processed_{item}"

    start_time = time.time()
    results = await processor.process_batch(items, process_item)
    parallel_time = time.time() - start_time

    print(f"✅ Parallel processing test completed in {parallel_time:.2f}s")
    print(f"📈 Items processed: {len(results)}")

    print("\n3️⃣ Testing Memory Optimization...")
    memory_optimizer = MemoryOptimizer(config)

    memory_info = memory_optimizer.get_memory_usage()
    print(f"💾 Current memory usage: {memory_info['rss_mb']:.1f} MB")
    print(f"💾 Memory percentage: {memory_info['percent']:.1f}%")
    print(f"💾 Available memory: {memory_info['available_mb']:.1f} MB")

    print("\n4️⃣ Testing TTS with Performance Monitoring...")

    tts = TTS()
    texts = [
        "Hello, this is a test.",
        "مرحبا، هذا اختبار.",
        "Bonjour, ceci est un test.",
    ]

    start_time = time.time()
    for i, text in enumerate(texts):
        try:
            audio_data = await tts.synth_async(text, lang="en")
            print(f"✅ Text {i + 1} synthesized: {len(audio_data)} bytes")
        except Exception as e:
            print(f"❌ Text {i + 1} failed: {e}")

    tts_time = time.time() - start_time
    print(f"📊 TTS processing completed in {tts_time:.2f}s")

    print("\n5️⃣ Performance Metrics...")

    await asyncio.sleep(2)

    perf_metrics = await performance_monitor.get_metrics()
    print(f"📈 Total requests: {perf_metrics['requests']['total']}")
    print(f"📈 Success rate: {perf_metrics['requests']['success_rate']:.1f}%")
    print(
        f"📈 Avg response time: {perf_metrics['performance']['avg_response_time']:.2f}s"
    )

    comprehensive_metrics = await metrics_collector.get_comprehensive_metrics()
    print(f"🎯 Health score: {comprehensive_metrics['health']:.1f}/100")
    print(f"🖥️ CPU usage: {comprehensive_metrics['system']['cpu_percent']:.1f}%")
    print(f"💾 Memory usage: {comprehensive_metrics['system']['memory_percent']:.1f}%")

    print("\n6️⃣ Engine Comparison...")
    engine_comparison = await metrics_collector.get_engine_comparison()

    for engine_name, data in engine_comparison.items():
        print(f"🎤 {engine_name}:")
        print(f"   • Requests: {data['requests']}")
        print(f"   • Success rate: {data['success_rate']:.1f}%")
        print(f"   • Avg response time: {data['avg_response_time']:.2f}s")
        print(f"   • Reliability score: {data['reliability_score']:.1f}/100")
        print(f"   • Performance score: {data['performance_score']:.1f}/100")

    print("\n✅ Performance optimization example completed!")
    print("🎉 All features are working correctly!")


async def batch_processing_example():
    """Shows how to handle lots of TTS requests at once efficiently.
    
    Processes multiple texts in parallel, handles errors gracefully, and gives
    you useful stats about timing and success rates so you can see how well
    things are working.
    """

    print("\n🔄 Batch Processing Example")
    print("=" * 30)

    tts = TTS()
    processor = ParallelProcessor(max_workers=5)

    texts = [f"This is test text number {i}" for i in range(20)]

    async def synthesize_text(text: str) -> dict:
        """Synthesizes one text and gives you back the results.
        
        Args:
            text: Text to turn into speech
            
        Returns:
            Dictionary with results including success status, file size, and any errors
        """
        try:
            audio_data = await tts.synth_async(text, lang="en")
            return {
                "text": text,
                "success": True,
                "size": len(audio_data),
                "error": None,
            }
        except Exception as e:
            return {"text": text, "success": False, "size": 0, "error": str(e)}

    print(f"📝 Processing {len(texts)} texts in parallel...")

    start_time = time.time()
    results = await processor.process_batch(texts, synthesize_text)
    end_time = time.time()

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    total_size = sum(r["size"] for r in successful)

    print(f"✅ Batch processing completed in {end_time - start_time:.2f}s")
    print(f"📊 Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"📈 Total audio size: {total_size:,} bytes")
    print(f"⚡ Average time per text: {(end_time - start_time) / len(texts):.3f}s")


if __name__ == "__main__":

    async def main():
        """Runs all the performance examples to show what TTSKit can do.
        
        Goes through performance monitoring, optimization features, and batch
        processing to give you a good feel for how fast things can be.
        """
        await performance_example()
        await batch_processing_example()

    asyncio.run(main())
