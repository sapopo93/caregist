"""Request-ID middleware for log correlation (F-39).

Pure-ASGI (not BaseHTTPMiddleware) so the ContextVar set here is reliably
visible to the route handler and all downstream logging in the same context.
"""

from __future__ import annotations

import uuid

from api.logging_config import request_id_var

_HEADER = b"x-request-id"
_MAX_LEN = 64


def _normalize(incoming: str | None) -> str:
    """Use a client-supplied id only if short and simple; otherwise mint one."""
    if incoming and len(incoming) <= _MAX_LEN and incoming.replace("-", "").isalnum():
        return incoming
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(_HEADER)
        request_id = _normalize(incoming.decode("latin-1") if incoming else None)
        token = request_id_var.set(request_id)

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers") or [])
                raw_headers = [(k, v) for k, v in raw_headers if k.lower() != _HEADER]
                raw_headers.append((_HEADER, request_id.encode("latin-1")))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            request_id_var.reset(token)
