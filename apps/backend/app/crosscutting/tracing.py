# apps/backend/app/crosscutting/tracing.py
"""
===============================================================================
MÓDULO: Tracing OpenTelemetry (opcional) + correlación con logs
===============================================================================

Objetivo
--------
- Activar spans cuando OTEL está habilitado
- Setear trace_id/span_id en contextvars para logs

Diseño
------
- Best-effort: si no hay libs de OTel, no rompe.
- No-op cuando está deshabilitado.

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  span() context manager

Responsabilidades:
  - Crear spans con atributos
  - Enriquecer contexto de logging con trace/span ids

Colaboradores:
  - app/context.py (trace_id_var, span_id_var)
  - crosscutting/config.py (otel_enabled)
===============================================================================
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Optional

_tracer: Optional[Any] = None
_enabled: bool = False


def _init_tracing() -> None:
    global _tracer, _enabled

    # Config: preferimos Settings si está disponible
    enabled = False
    try:
        from .config import get_settings

        enabled = bool(get_settings().otel_enabled)
    except Exception:
        enabled = False

    if not enabled:
        _enabled = False
        _tracer = None
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        resource = Resource.create({"service.name": "rag-corp-api"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer("rag-corp")
        _enabled = True
    except Exception:
        _enabled = False
        _tracer = None


_init_tracing()


@contextmanager
def span(name: str, attributes: Optional[dict] = None) -> Generator[Any, None, None]:
    """
    Uso:
      with span("embed_query", {"len": len(query)}):
          ...

    Si tracing no está habilitado, es no-op.
    """
    if not _enabled or _tracer is None:
        yield None
        return

    with _tracer.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                try:
                    s.set_attribute(k, v)
                except Exception:
                    pass

        # Correlación con logs
        try:
            from ..context import span_id_var, trace_id_var

            ctx = s.get_span_context()
            trace_id_var.set(format(ctx.trace_id, "032x"))
            span_id_var.set(format(ctx.span_id, "016x"))
        except Exception:
            pass

        yield s


def is_tracing_enabled() -> bool:
    return bool(_enabled and _tracer is not None)
