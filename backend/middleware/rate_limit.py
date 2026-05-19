"""
Per-user rate limiting middleware.
In-memory token bucket — resets on server restart.
For MVP this is fine; production at scale would use Redis.
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitBucket:
    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = max_tokens
        self.last_refill = time.time()

    def consume(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


# Path pattern -> rate limit config
# "max" = bucket size (burst capacity), "refill" = tokens per second
RATE_LIMITS = {
    "/suggest": {"max": 10, "refill": 0.1},          # 10 burst, 1 per 10s
    "/strategy/stream": {"max": 3, "refill": 0.02},  # 3 burst, 1 per 50s
    "/strategy/refresh": {"max": 5, "refill": 0.05},  # 5 burst, 1 per 20s
    "/simulate/game": {"max": 5, "refill": 0.05},    # 5 burst, 1 per 20s
    "/simulate/hand": {"max": 10, "refill": 0.1},    # 10 burst, 1 per 10s
    "/simulate/custom": {"max": 5, "refill": 0.05},  # 5 burst, 1 per 20s
    "/roles/auto-suggest": {"max": 5, "refill": 0.05},
    "/auth/login": {"max": 10, "refill": 0.1},       # brute force protection
    "/auth/signup": {"max": 3, "refill": 0.01},      # 3 burst, 1 per 100s
    "/auth/refresh": {"max": 10, "refill": 0.1},     # 10 burst, 1 per 10s
}

DEFAULT_LIMIT = {"max": 60, "refill": 1.0}  # general endpoints: 60/min


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.buckets: dict[str, dict[str, RateLimitBucket]] = defaultdict(dict)

    def _get_user_key(self, request: Request) -> str:
        """Use token hash if authenticated, else client IP."""
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            return f"token:{hash(auth)}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    def _match_config(self, path: str) -> tuple[str, dict]:
        """Find the rate limit config for this request path."""
        for pattern, config in RATE_LIMITS.items():
            if pattern in path:
                return pattern, config
        return "default", DEFAULT_LIMIT

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        user_key = self._get_user_key(request)
        pattern_key, config = self._match_config(request.url.path)

        # Get or create bucket
        if pattern_key not in self.buckets[user_key]:
            self.buckets[user_key][pattern_key] = RateLimitBucket(
                max_tokens=config["max"],
                refill_rate=config["refill"],
            )

        bucket = self.buckets[user_key][pattern_key]
        if not bucket.consume():
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before trying again."},
            )

        # Periodic cleanup of stale buckets
        total = sum(len(b) for b in self.buckets.values())
        if total > 1000:
            self._cleanup()

        return await call_next(request)

    def _cleanup(self):
        now = time.time()
        stale = [
            key for key, buckets in self.buckets.items()
            if all(now - b.last_refill > 3600 for b in buckets.values())
        ]
        for key in stale:
            del self.buckets[key]