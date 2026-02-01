# apps/backend/app/crosscutting/middleware.py
"""
===============================================================================
MÓDULO: Middlewares HTTP (contexto + límites de payload)
===============================================================================

Objetivo
--------
1) RequestContextMiddleware:
   - Generar/propagar request_id
   - Setear contextvars (method/path)
   - Log y métricas por request

2) BodyLimitMiddleware:
   - Defender la API de payloads gigantes (incluyendo chunked uploads)

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componentes:
  - RequestContextMiddleware
  - BodyLimitMiddleware

Responsabilidades:
  - Observabilidad (request_id + logs + métricas)
  - Seguridad (límite estricto de body)

Colaboradores:
  - app/context.py
  - crosscutting/metrics.py
  - crosscutting/error_responses.py
===============================================================================
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..context import clear_context, http_method_var, http_path_var, request_id_var
from .error_responses import (
    PROBLEM_JSON_MEDIA_TYPE,
    AppHTTPException,
    ErrorCode,
    ErrorDetail,
)
from .logger import logger


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      RequestContextMiddleware

    Responsabilidades:
      - Generar/aceptar X-Request-Id
      - Setear contextvars para correlación de logs
      - Emitir logs y métricas por request
      - Garantizar clear_context() para evitar leaks

    Colaboradores:
      - crosscutting.metrics.record_request_metrics
      - crosscutting.logger
    ----------------------------------------------------------------------------
    """

    _QUIET_PATHS = {"/healthz", "/metrics"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = (request.headers.get("x-request-id") or "").strip()
        request_id = (
            incoming if self._is_valid_request_id(incoming) else str(uuid.uuid4())
        )

        request_id_var.set(request_id)
        http_method_var.set(request.method)
        http_path_var.set(request.url.path)

        request.state.request_id = request_id

        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            latency = time.perf_counter() - start
            logger.exception(
                "request falló",
                extra={"status_code": 500, "latency_ms": round(latency * 1000, 2)},
            )
            raise
        finally:
            latency = time.perf_counter() - start

            # Headers de correlación siempre que se haya generado respuesta
            # (si hubo excepción, FastAPI generará la respuesta luego)
            try:
                # Métricas (best-effort)
                from .metrics import record_request_metrics

                record_request_metrics(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    latency_seconds=latency,
                )
            except Exception:
                pass

            # Log de finalización (evitar spam en endpoints de salud)
            if request.url.path not in self._QUIET_PATHS:
                logger.info(
                    "request completado",
                    extra={
                        "status_code": status_code,
                        "latency_ms": round(latency * 1000, 2),
                    },
                )

            clear_context()

    @staticmethod
    def _is_valid_request_id(value: str) -> bool:
        # Aceptamos UUIDs y también ids cortos razonables.
        if not value:
            return False
        if len(value) > 128:
            return False
        return True


class _BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      BodyLimitMiddleware

    Responsabilidades:
      - Rechazar requests cuyo body exceda max_body_bytes
      - Funciona tanto con Content-Length como con transferencia chunked

    Colaboradores:
      - crosscutting.config.get_settings()
      - crosscutting.error_responses (RFC7807)
      - crosscutting.logger
    ----------------------------------------------------------------------------
    """

    def __init__(self, app):
        from .config import get_settings

        self.app = app
        self._max_bytes = get_settings().max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Parse headers (bytes -> str)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        path = scope.get("path", "")

        # request_id (si llega, lo propagamos; sino generamos)
        req_id = (headers.get("x-request-id") or "").strip() or str(uuid.uuid4())

        # Si hay Content-Length y excede, cortamos inmediato
        cl = headers.get("content-length")
        if cl:
            try:
                if int(cl) > self._max_bytes:
                    logger.warning(
                        "payload demasiado grande (por content-length)",
                        extra={
                            "content_length": cl,
                            "max_bytes": self._max_bytes,
                            "path": path,
                        },
                    )
                    await self._send_413(send, path=path, request_id=req_id)
                    return
            except ValueError:
                # Content-Length inválido -> seguimos y controlamos por streaming
                pass

        started = False

        async def send_wrapper(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                # Propagar X-Request-Id
                hdrs = list(message.get("headers", []))
                hdrs.append((b"x-request-id", req_id.encode()))
                message["headers"] = hdrs
            await send(message)

        received = 0

        async def receive_limited():
            nonlocal received
            msg = await receive()
            if msg["type"] == "http.request":
                body = msg.get("body", b"") or b""
                received += len(body)
                if received > self._max_bytes:
                    raise _BodyTooLarge()
            return msg

        try:
            await self.app(scope, receive_limited, send_wrapper)
        except _BodyTooLarge:
            # Si ya arrancó la respuesta, no podemos enviar otra sin romper el protocolo
            if started:
                logger.error(
                    "payload excedió límite luego de iniciar respuesta",
                    extra={"path": path},
                )
                raise
            logger.warning(
                "payload demasiado grande (streaming)",
                extra={
                    "received_bytes": received,
                    "max_bytes": self._max_bytes,
                    "path": path,
                },
            )
            await self._send_413(send, path=path, request_id=req_id)

    async def _send_413(self, send, *, path: str, request_id: str) -> None:
        detail = (
            f"Request body demasiado grande. Máximo permitido: {self._max_bytes} bytes"
        )

        problem = ErrorDetail(
            type="about:blank/payload_too_large",
            title="Payload Too Large",
            status=413,
            detail=detail,
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            instance=path,
            errors=[{"request_id": request_id}],
        ).model_dump(exclude_none=True)

        body = (str(problem)).encode("utf-8")
        # Mejor JSON real (sin depender de json aquí): reusar json en error_responses sería ok,
        # pero mantenemos esto simple y robusto.
        import json

        body = json.dumps(problem, ensure_ascii=False).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", PROBLEM_JSON_MEDIA_TYPE.encode()),
                    (b"x-request-id", request_id.encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
