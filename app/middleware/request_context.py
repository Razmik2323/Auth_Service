import logging
import time
from collections.abc import Iterable
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import request_id_ctx

REQUEST_ID_HEADER = "x-request-id"

logger = logging.getLogger("app.request")


class RequestContextMiddleware:
    """Assign a request id and log request completion."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Bind a request id for the lifetime of an HTTP request."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = _resolve_request_id(scope)
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request.completed",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_ctx.reset(token)


def _resolve_request_id(scope: Scope) -> str:
    """Reuse an inbound request id header or generate a new one."""
    target = REQUEST_ID_HEADER.encode("latin-1")
    headers: Iterable[tuple[bytes, bytes]] = scope.get("headers", [])
    for name, value in headers:
        if name == target:
            return value.decode("latin-1")
    return str(uuid4())
