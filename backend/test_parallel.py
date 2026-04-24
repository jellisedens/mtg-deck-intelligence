import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from services.strategy_profiler import _call_impact_batch

executor = ThreadPoolExecutor(max_workers=10)

system = 'Respond with only valid JSON array: [{"card_name": "Test", "score": 5, "reason": "test"}]'
user_msg = "Rate this card: Lightning Bolt, Instant, {R}, deals 3 damage"

async def test():
    loop = asyncio.get_event_loop()

    t = time.time()
    for _ in range(3):
        await loop.run_in_executor(executor, lambda: _call_impact_batch(system, user_msg))
    seq_time = time.time() - t
    print(f"Sequential (3 calls): {seq_time:.1f}s")

    t = time.time()
    futures = [
        loop.run_in_executor(executor, lambda: _call_impact_batch(system, user_msg))
        for _ in range(3)
    ]
    await asyncio.gather(*futures)
    par_time = time.time() - t
    print(f"Parallel (3 calls): {par_time:.1f}s")
    print(f"Speedup: {seq_time/par_time:.1f}x")

asyncio.run(test())