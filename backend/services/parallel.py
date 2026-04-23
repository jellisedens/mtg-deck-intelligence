"""
Parallel execution utility for batched AI calls.
Runs synchronous OpenAI calls concurrently using thread pool.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

# Shared thread pool for AI calls
_executor = ThreadPoolExecutor(max_workers=8)


async def run_parallel(tasks: list) -> list:
    """
    Run a list of synchronous functions in parallel using threads.
    
    Args:
        tasks: list of (function, args, kwargs) tuples
    
    Returns:
        list of results in the same order as tasks
    """
    loop = asyncio.get_event_loop()
    
    futures = []
    for func, args, kwargs in tasks:
        future = loop.run_in_executor(_executor, lambda f=func, a=args, k=kwargs: f(*a, **k))
        futures.append(future)
    
    results = await asyncio.gather(*futures, return_exceptions=True)
    
    # Replace exceptions with None so one failure doesn't kill everything
    cleaned = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Parallel task {i} failed: {result}")
            cleaned.append(None)
        else:
            cleaned.append(result)
    
    return cleaned