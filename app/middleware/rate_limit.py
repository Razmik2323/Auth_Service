import json
import logging
import time
from collections.abc import Iterable

from redis.asyncio import Redis
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings

logger = logging.getLogger("app.ratelimit")

_EXCLUDED_PATHS = frozenset({"/health"})
_AUTH_PREFIX = "/api/v1/auth"


class RateLimitMiddleware:
    """Fixed-window per-IP rate limiting backed by Redis."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject requests exceeding the per-IP window with a 429."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        app = scope["app"]
        settings: Settings = app.state.settings
        path: str = scope["path"]
        if not settings.rate_limit_enabled or path in _EXCLUDED_PATHS:
            await self._app(scope, receive, send)
            return

        category, max_requests, window = self._limits(settings, path)
        identifier = _client_identifier(scope)
        allowed, retry_after = await self._check(
            app.state.redis, category, identifier, max_requests, window
        )
        if allowed:
            await self._app(scope, receive, send)
            return
        await self._reject(retry_after, send)

    def _limits(self, settings: Settings, path: str) -> tuple[str, int, int]:
        """Return the category and window limits applicable to a path."""
        if path.startswith(_AUTH_PREFIX):
            return "auth", settings.rate_limit_auth_max, settings.rate_limit_auth_window_seconds
        return (
            "default",
            settings.rate_limit_default_max,
            settings.rate_limit_default_window_seconds,
        )

    async def _check(
        self, redis: Redis, category: str, identifier: str, max_requests: int, window: int
    ) -> tuple[bool, int]:
        """Increment the window counter and report whether the request is allowed."""
        now = int(time.time())
        window_start = now - (now % window)
        key = f"rl:{category}:{identifier}:{window_start}"
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()
        count = int(results[0])
        if count > max_requests:
            return False, window - (now % window)
        return True, 0

    async def _reject(self, retry_after: int, send: Send) -> None:
        """Send a 429 response with a Retry-After header."""
        body = json.dumps({"detail": "rate limit exceeded", "code": "rate_limited"}).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"retry-after", str(retry_after).encode()),
        ]
        await send({"type": "http.response.start", "status": 429, "headers": headers})
        await send({"type": "http.response.body", "body": body})


def _client_identifier(scope: Scope) -> str:
    """Return the real client IP, preferring the trusted X-Real-IP header."""
    headers: Iterable[tuple[bytes, bytes]] = scope.get("headers", [])
    for name, value in headers:
        if name == b"x-real-ip":
            return value.decode("latin-1")
    client = scope.get("client")
    if client:
        return str(client[0])
    return "unknown"
