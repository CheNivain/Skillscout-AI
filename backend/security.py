"""Local password/session primitives. No passwords or session tokens are persisted in clear text."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


class RateLimiter:
    """Bounded, thread-safe rate windows for this single local gateway process."""

    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._events) > 10000:
                self._events = defaultdict(deque, {k: v for k, v in self._events.items() if v and v[-1] > now - 3600})
            events = self._events[key]
            while events and events[0] <= now - seconds:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True


limiter = RateLimiter()


class BodyLimitMiddleware:
    """Bound actual streamed bytes before Starlette/Pydantic parse a request body."""

    def __init__(self, app, limit: int = 1_500_000):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse

        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
            if declared < 0:
                raise ValueError
            if declared > self.limit:
                return await JSONResponse({"detail": "Request body is too large"}, status_code=413)(scope, receive, send)
        except ValueError:
            return await JSONResponse({"detail": "Invalid content length"}, status_code=400)(scope, receive, send)
        chunks, length = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            length += len(body)
            if length > self.limit:
                return await JSONResponse({"detail": "Request body is too large"}, status_code=413)(scope, receive, send)
            chunks.append(body)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
