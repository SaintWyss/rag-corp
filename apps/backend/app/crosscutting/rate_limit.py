# apps/backend/app/crosscutting/rate_limit.py
"""
===============================================================================
MÓDULO: Rate limiting (Token Bucket) - in-memory
===============================================================================

Objetivo
--------
Limitar abuso por:
- API key (si existe)
- IP (fallback)

Incluye:
- Token bucket (suaviza bursts)
- Headers x-ratelimit-remaining / x-ratelimit-limit
- Respuesta RFC7807 con Retry-After

Mejoras senior incluidas
------------------------
- Limpieza por TTL para evitar leak de memoria
- Límite de buckets con eviction simple (protección adicional)

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componentes:
  - TokenBucket
  - RateLimitMiddleware

Responsabilidades:
  - Decidir allow/deny
  - Emitir 429 con Retry-After
  - Mantener estado thread-safe

Colaboradores:
  - crosscutting.config
  - crosscutting.error_responses
  - crosscutting.logger
===============================================================================
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from .error_responses import app_exception_handler, rate_limited
from .logger import logger


@dataclass
class Bucket:
    tokens: float
    last_refill: float
    last_seen: float


class TokenBucket:
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      TokenBucket

    Responsabilidades:
      - Implementar algoritmo token-bucket por key
      - Refill por tiempo
      - TTL cleanup
      - Eviction por máximo de buckets

    Colaboradores:
      - RateLimitMiddleware
    ----------------------------------------------------------------------------
    """

    def __init__(
        self,
        rps: float,
        burst: int,
        *,
        ttl_seconds: int = 3600,
        max_buckets: int = 10_000,
    ):
        if rps <= 0:
            raise ValueError("rps debe ser > 0")
        if burst <= 0:
            raise ValueError("burst debe ser > 0")
        self.rps = float(rps)
        self.burst = int(burst)

        self.ttl_seconds = int(ttl_seconds)
        self.max_buckets = int(max_buckets)

        self._buckets: "OrderedDict[str, Bucket]" = OrderedDict()
        self._lock = threading.Lock()
        self._ops = 0

    def consume(self, key: str) -> tuple[bool, float]:
        with self._lock:
            now = time.monotonic()
            self._ops += 1

            self._cleanup_if_needed(now)

            bucket = self._get_or_create_bucket(key, now)
            self._refill(bucket, now)
            bucket.last_seen = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                # LRU touch
                self._buckets.move_to_end(key, last=True)
                return True, 0.0

            tokens_needed = 1 - bucket.tokens
            retry_after = tokens_needed / self.rps
            self._buckets.move_to_end(key, last=True)
            return False, retry_after

    def get_remaining(self, key: str) -> int:
        with self._lock:
            now = time.monotonic()
            b = self._buckets.get(key)
            if not b:
                return self.burst
            self._refill(b, now)
            return int(b.tokens)

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()

    # --------------------------- internos ---------------------------

    def _get_or_create_bucket(self, key: str, now: float) -> Bucket:
        b = self._buckets.get(key)
        if b:
            return b

        # Eviction si excede máximo
        if len(self._buckets) >= self.max_buckets:
            self._buckets.popitem(last=False)

        b = Bucket(tokens=float(self.burst), last_refill=now, last_seen=now)
        self._buckets[key] = b
        return b

    def _refill(self, bucket: Bucket, now: float) -> None:
        elapsed = now - bucket.last_refill
        if elapsed <= 0:
            return
        bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.rps)
        bucket.last_refill = now

    def _cleanup_if_needed(self, now: float) -> None:
        # Cada ~256 operaciones hacemos cleanup para amortizar costo
        if (self._ops & 0xFF) != 0:
            return

        ttl = self.ttl_seconds
        if ttl <= 0:
            return

        # Remover buckets viejos por last_seen
        to_delete = []
        for k, b in self._buckets.items():
            if now - b.last_seen > ttl:
                to_delete.append(k)
            else:
                # Como es OrderedDict LRU-ish, podemos cortar temprano si están frescos
                break

        for k in to_delete:
            self._buckets.pop(k, None)


_rate_limiter: Optional[TokenBucket] = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> TokenBucket:
    global _rate_limiter
    with _limiter_lock:
        if _rate_limiter is None:
            from .config import get_settings

            s = get_settings()
            _rate_limiter = TokenBucket(rps=s.rate_limit_rps, burst=s.rate_limit_burst)
        return _rate_limiter


def reset_rate_limiter() -> None:
    global _rate_limiter
    with _limiter_lock:
        _rate_limiter = None


def is_rate_limiting_enabled() -> bool:
    from .config import get_settings

    s = get_settings()
    return s.rate_limit_rps > 0 and s.rate_limit_burst > 0


def get_client_identifier(request) -> str:
    # 1) API key hash (si auth la setea)
    if hasattr(request.state, "api_key_hash"):
        return f"key:{request.state.api_key_hash}"

    # 2) Proxy header
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
        return f"ip:{ip}"

    # 3) IP directa
    client = request.client
    if client:
        return f"ip:{client.host}"

    return "ip:unknown"


class RateLimitMiddleware:
    """
    ASGI middleware de rate limit.

    - Excluye endpoints típicos de infraestructura.
    - Evita overhead cuando está deshabilitado.
    """

    EXCLUDED_PATHS = {"/healthz", "/metrics", "/openapi.json", "/docs", "/redoc"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not is_rate_limiting_enabled():
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        if scope.get("method", "").upper() == "OPTIONS":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request

        request = Request(scope, receive)
        client_id = get_client_identifier(request)

        limiter = get_rate_limiter()
        allowed, retry_after = limiter.consume(client_id)

        if not allowed:
            retry_after_int = max(1, int(retry_after) + 1)

            logger.warning(
                "rate limit excedido",
                extra={
                    "client_id": client_id,
                    "path": path,
                    "retry_after": retry_after_int,
                },
            )

            exc = rate_limited(retry_after_int)
            headers = getattr(exc, "headers", None) or {}
            headers.update(
                {
                    "x-ratelimit-remaining": "0",
                    "x-ratelimit-limit": str(limiter.burst),
                }
            )
            exc.headers = headers

            response = await app_exception_handler(request, exc)
            await response(scope, receive, send)
            return

        remaining = limiter.get_remaining(client_id)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                hdrs = list(message.get("headers", []))
                hdrs.append((b"x-ratelimit-remaining", str(remaining).encode()))
                hdrs.append((b"x-ratelimit-limit", str(limiter.burst).encode()))
                message["headers"] = hdrs
            await send(message)

        await self.app(scope, receive, send_with_headers)
