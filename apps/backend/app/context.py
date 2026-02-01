"""
===============================================================================
TARJETA CRC — app/context.py (Contexto por request / job)
===============================================================================

Responsabilidades:
  - Mantener contexto “request-scoped” usando ContextVars (async-safe).
  - Permitir correlación de logs/métricas/trazas sin pasar parámetros por todo el stack.
  - Proveer helpers mínimos: set_*(), get_context_dict(), clear_context().

Colaboradores:
  - app.crosscutting.middleware: setea request_id/method/path al inicio del request.
  - app.crosscutting.logger: enriquece logs leyendo get_context_dict().
  - app.crosscutting.tracing: setea trace_id/span_id si OTel está habilitado.
  - app.worker.jobs: setea request_id por job y limpia contexto al finalizar.

Patrones aplicados:
  - Ambient Context (controlado y explícito).
  - Async-safe “thread-local” (ContextVar).

Restricciones:
  - Solo tipos primitivos (str) para serialización segura.
  - Defaults vacíos ("") para evitar None y simplificar JSON.
===============================================================================
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Final

# =============================================================================
# ContextVars: cada variable representa un dato correlacionable del request/job
# =============================================================================

# Identificador de request o job (idealmente UUID o ID estable).
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Identificadores de traza (hex) si está habilitado tracing (OpenTelemetry).
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
span_id_var: ContextVar[str] = ContextVar("span_id", default="")

# Metadatos HTTP básicos para logs (método y path).
http_method_var: ContextVar[str] = ContextVar("http_method", default="")
http_path_var: ContextVar[str] = ContextVar("http_path", default="")

# Claves estándar (para consistencia al construir dicts).
_CTX_REQUEST_ID: Final[str] = "request_id"
_CTX_TRACE_ID: Final[str] = "trace_id"
_CTX_SPAN_ID: Final[str] = "span_id"
_CTX_METHOD: Final[str] = "method"
_CTX_PATH: Final[str] = "path"


# =============================================================================
# API pública (usada por logger/middleware/worker)
# =============================================================================


def set_request_context(
    *, request_id: str = "", method: str = "", path: str = ""
) -> None:
    """
    Setea el contexto mínimo del request.

    Regla:
      - Strings vacíos significan “no disponible”.
    """
    request_id_var.set(request_id or "")
    http_method_var.set(method or "")
    http_path_var.set(path or "")


def set_trace_context(*, trace_id: str = "", span_id: str = "") -> None:
    """
    Setea el contexto de tracing (si aplica).
    """
    trace_id_var.set(trace_id or "")
    span_id_var.set(span_id or "")


def get_context_dict() -> dict[str, str]:
    """
    Devuelve el contexto actual como dict, omitiendo claves vacías.

    Uso típico:
      - Enriquecimiento de logs estructurados.
    """
    ctx: dict[str, str] = {}

    if val := request_id_var.get():
        ctx[_CTX_REQUEST_ID] = val
    if val := trace_id_var.get():
        ctx[_CTX_TRACE_ID] = val
    if val := span_id_var.get():
        ctx[_CTX_SPAN_ID] = val
    if val := http_method_var.get():
        ctx[_CTX_METHOD] = val
    if val := http_path_var.get():
        ctx[_CTX_PATH] = val

    return ctx


def clear_context() -> None:
    """
    Limpia el contexto al final del request/job.

    Importante:
      - Esto evita “filtración de contexto” entre requests cuando hay workers async.
    """
    request_id_var.set("")
    trace_id_var.set("")
    span_id_var.set("")
    http_method_var.set("")
    http_path_var.set("")
