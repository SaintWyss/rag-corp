"""app.infrastructure.services.retry

Name: Retry Helper with Exponential Backoff + Jitter

Qué es
------
Utilidad cross-cutting de **resiliencia** para llamadas a servicios externos.
Implementa:
  - Clasificación de errores: **transient** (reintentar) vs **permanent** (fail-fast)
  - Decorator de `tenacity` para aplicar **exponential backoff + jitter**
  - Logging estructurado de intentos de retry (incluye correlation/request id cuando está disponible)

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Infrastructure (crosscutting/resilience)
- Rol: Proveer un mecanismo reutilizable para providers externos (Google, HTTP, etc.)

Patrones de diseño
------------------
- **Decorator**: `create_retry_decorator()` retorna un decorator que envuelve una función.
- **Policy Object** (implícito): `is_transient_error()` es la política de clasificación.
- **Fail-fast**: errores permanentes no se reintentan.

SOLID
-----
- SRP: este módulo solo trata resiliencia/observabilidad (no hace negocio).
- OCP: podés extender la clasificación (códigos/excepciones) sin tocar consumidores.
- DIP: los consumidores dependen de una abstracción simple (decorator), no de detalles.

CRC (Component Card)
--------------------
Component: retry helper
Responsibilities:
  - Decidir qué errores son reintentables
  - Proveer un decorator estándar (tenacity) con backoff+jitter
  - Loguear intentos y contexto útil para debugging/observabilidad
Collaborators:
  - tenacity (motor de retry)
  - crosscutting.config.get_settings (config de attempts/delays)
  - crosscutting.logger (logging estructurado)
Constraints:
  - Reintentar SOLO errores transitorios (429, 5xx, timeouts, connection issues)
  - No reintentar errores permanentes (400, 401, 403, 404)
  - Jitter para evitar thundering herd
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ...crosscutting.config import get_settings
from ...crosscutting.logger import logger

T = TypeVar("T")


# ---------------------------------------------------------------------------
# HTTP code policies
# ---------------------------------------------------------------------------

# R: HTTP status codes que indican fallas transitorias (reintentables)
TRANSIENT_HTTP_CODES: frozenset[int] = frozenset(
    {
        408,  # Request Timeout
        429,  # Too Many Requests (rate limit)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    }
)

# R: HTTP status codes que indican fallas permanentes (no reintentar)
PERMANENT_HTTP_CODES: frozenset[int] = frozenset(
    {
        400,  # Bad Request
        401,  # Unauthorized
        403,  # Forbidden
        404,  # Not Found
    }
)


def get_http_status_code(exception: BaseException) -> int | None:
    """R: Extrae un status code HTTP desde distintos tipos de exception.

    Soporta (best-effort):
      - google.api_core.exceptions.* (atributo `code`)
      - httpx.HTTPStatusError (exception.response.status_code)
      - excepciones de SDKs que expongan `status_code`

    Returns:
        int | None: HTTP status code si se encuentra, o None si no.
    """

    # R: Google API Core exceptions suelen exponer `code`.
    if hasattr(exception, "code"):
        code = getattr(exception, "code")
        # R: En algunos SDKs `code` puede ser gRPC status; filtramos a códigos HTTP (>=100).
        if isinstance(code, int) and code >= 100:
            return code

    # R: httpx.HTTPStatusError expone `response.status_code`.
    resp = getattr(exception, "response", None)
    if resp is not None and hasattr(resp, "status_code"):
        status_code = getattr(resp, "status_code")
        if isinstance(status_code, int):
            return status_code

    # R: Algunos SDKs exponen `status_code` directamente.
    status_code = getattr(exception, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    return None


def is_transient_error(exception: BaseException) -> bool:
    """R: Decide si un error es transitorio (reintentar) o permanente (fail-fast).

    Reglas (en orden):
      1) Si hay status code HTTP: permanent → False, transient → True.
      2) Si es una excepción típica de timeout/connection (built-in): True.
      3) Heurística por nombre/mensaje (best-effort) para SDKs que no tipifican bien.
      4) Default: fail-fast (False) para no reintentar errores desconocidos.
    """

    # R: 1) Clasificación por status code
    status_code = get_http_status_code(exception)
    if status_code is not None:
        if status_code in PERMANENT_HTTP_CODES:
            return False
        if status_code in TRANSIENT_HTTP_CODES:
            return True

    # R: 2) Tipos built-in comunes (sin depender de librerías opcionales)
    if isinstance(exception, (TimeoutError, ConnectionError, OSError)):
        # R: OSError cubre casos como "Connection reset", "Network unreachable".
        #     Es un poco amplio, pero preferimos resiliencia para IO/red.
        return True

    # R: 3) Heurística por nombre de clase (SDKs variados)
    exception_name = type(exception).__name__.lower()
    transient_name_patterns = (
        "timeout",
        "timedout",
        "connection",
        "connect",
        "temporary",
        "unavailable",
        "resourceexhausted",
        "deadline",
        "aborted",
        "cancelled",
    )
    if any(p in exception_name for p in transient_name_patterns):
        return True

    # R: 4) Heurística por mensaje (último recurso)
    message = str(exception).lower()
    transient_message_patterns = (
        "rate limit",
        "too many requests",
        "quota exceeded",
        "temporarily unavailable",
        "service unavailable",
        "connection reset",
        "connection refused",
        "network is unreachable",
        "timed out",
        "deadline exceeded",
    )
    if any(p in message for p in transient_message_patterns):
        return True

    # R: Default conservador: si no sabemos, NO reintentamos.
    return False


def _extract_request_id(retry_state: RetryCallState) -> Optional[str]:
    """R: Extrae request_id/correlation_id de kwargs para observabilidad.

    Nota:
      - Tenacity mantiene `args`/`kwargs` dentro de `RetryCallState`.
      - Esta función es best-effort (si no hay id, retorna None).
    """
    kwargs = getattr(retry_state, "kwargs", None) or {}
    for key in ("request_id", "correlation_id", "trace_id"):
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _log_retry(retry_state: RetryCallState) -> None:
    """R: Loguea cada intento antes de dormir (before_sleep).

    Incluye:
      - nombre de función
      - intento actual
      - tiempo de espera hasta el próximo intento
      - excepción previa
      - request_id/correlation_id si existe en kwargs
    """

    fn = getattr(retry_state, "fn", None)
    fn_name = getattr(fn, "__name__", "unknown")
    attempt = getattr(retry_state, "attempt_number", 0)
    wait_time = (
        retry_state.next_action.sleep
        if getattr(retry_state, "next_action", None) is not None
        else 0
    )

    exc: Optional[BaseException] = None
    if getattr(retry_state, "outcome", None) is not None:
        exc = retry_state.outcome.exception()

    request_id = _extract_request_id(retry_state)

    # R: Logging estructurado (sin interpolar información importante en el mensaje)
    logger.warning(
        "Retrying external call",
        extra={
            "function": fn_name,
            "attempt": attempt,
            "wait_seconds": round(float(wait_time), 2),
            "request_id": request_id,
            "error": str(exc) if exc else None,
            "error_type": type(exc).__name__ if exc else None,
        },
    )


def create_retry_decorator(
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """R: Crea un decorator `tenacity` con exponential backoff + jitter.

    Config:
      - stop: `stop_after_attempt(max_attempts)`
      - wait: `wait_exponential_jitter(initial=base_delay, max=max_delay)`
      - retry: solo si `is_transient_error(exception)`
      - before_sleep: `_log_retry`
      - reraise: True (propaga la última excepción)
    """
    settings = get_settings()

    # R: Usar overrides solo si fueron provistos explícitamente.
    _max_attempts = (
        settings.retry_max_attempts if max_attempts is None else max_attempts
    )
    _base_delay = (
        settings.retry_base_delay_seconds if base_delay is None else float(base_delay)
    )
    _max_delay = (
        settings.retry_max_delay_seconds if max_delay is None else float(max_delay)
    )

    if _max_attempts <= 0:
        raise ValueError("max_attempts must be > 0")
    if _base_delay < 0:
        raise ValueError("base_delay must be >= 0")
    if _max_delay <= 0:
        raise ValueError("max_delay must be > 0")

    # R: Decorator de tenacity. `wait_exponential_jitter` ya agrega jitter.
    return retry(
        stop=stop_after_attempt(_max_attempts),
        wait=wait_exponential_jitter(
            initial=_base_delay,
            max=_max_delay,
            jitter=_base_delay,  # R: jitter adicional best-effort (mantiene compatibilidad)
        ),
        retry=retry_if_exception(is_transient_error),
        before_sleep=_log_retry,
        reraise=True,
    )


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """R: Decorator simple que aplica retry con settings por defecto.

    Nota de diseño:
      - Creamos la función reintentable UNA vez en tiempo de decoración (no en cada llamada)
        para reducir overhead y hacer más predecible el comportamiento.
    """

    # R: Construimos la función reintentable una sola vez.
    decorator = create_retry_decorator()
    wrapped_func = decorator(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return wrapped_func(*args, **kwargs)

    return wrapper
