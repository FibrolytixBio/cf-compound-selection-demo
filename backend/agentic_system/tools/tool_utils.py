import fcntl
import json
import time
import asyncio
from pathlib import Path
import diskcache
from functools import wraps


def tool_cache(name: str, enabled: bool = False):
    """
    Decorator to cache function results using diskcache.
    Creates a cache directory at /tmp/{name}_cache.

    Args:
        name (str): Name for the cache (e.g., "chembl", "pubchem")
        enabled (bool): Whether to enable caching. Defaults to False.

    Returns:
        Decorated function with caching enabled if enabled=True, otherwise the original function

    Usage:
        @tool_cache("chembl", enabled=True)
        def my_function(arg1, arg2):
            return expensive_operation(arg1, arg2)
    """

    def decorator(func):
        if not enabled:
            return func

        cache = diskcache.Cache(f"/tmp/{name}_cache")

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a hashable key from function name and arguments
            key = (func.__name__, args, tuple(sorted(kwargs.items())))

            # Check cache first
            if key in cache:
                return cache[key]

            # Call function and cache result with 3-day expiration
            result = func(*args, **kwargs)
            expire_time = time.time() + (3 * 24 * 60 * 60)  # 3 days in seconds
            cache.set(key, result, expire=expire_time)
            return result

        return wrapper

    return decorator


class FileBasedRateLimiter:
    def __init__(
        self, max_requests: int = 3, time_window: float = 1.0, name: str = "default"
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.state_file = Path(f"/tmp/{name}_rate_limiter.json")

    async def acquire(self):
        """Async version for async use"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._acquire_sync)

    def acquire_sync(self):
        """Synchronous version for non-async use"""
        self._acquire_sync()

    def _acquire_sync(self):
        # Create file if it doesn't exist
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"requests": []}))

        # Acquire exclusive lock
        with open(self.state_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                current_time = time.time()

                # Clean old requests
                data["requests"] = [
                    req
                    for req in data["requests"]
                    if current_time - req < self.time_window
                ]

                # Check if we need to wait
                if len(data["requests"]) >= self.max_requests:
                    oldest = data["requests"][0]
                    wait_time = self.time_window - (current_time - oldest)
                    if wait_time > 0:
                        time.sleep(wait_time)
                        current_time = time.time()
                        data["requests"] = [
                            req
                            for req in data["requests"]
                            if current_time - req < self.time_window
                        ]

                # Add current request
                data["requests"].append(current_time)

                # Write back
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
