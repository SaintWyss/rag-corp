"""
Name: OpenTelemetry Tracing (Optional)

Responsibilities:
  - Initialize OpenTelemetry tracing when OTEL_ENABLED=1
  - Provide span creation helpers
  - Correlate trace_id/span_id with logs

Collaborators:
  - context.py: Sets trace_id/span_id for log enrichment
  - config.py: Reads OTEL_ENABLED setting

Constraints:
  - Completely optional (no-op when disabled)
  - Lazy initialization (don't fail if otel not installed)
  - Zero overhead when disabled

Notes:
  - Requires: opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi
  - Configure exporter via OTEL_EXPORTER_* env vars
  - Default: console exporter for development
"""

import os
from typing import Optional, Any, Generator
from contextlib import contextmanager

# R: Check if tracing is enabled
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "0") == "1"

# R: Lazy imports to make opentelemetry optional
_tracer: Optional[Any] = None
_trace_module: Optional[Any] = None


def _init_tracing() -> None:
    """R: Initialize OpenTelemetry tracing."""
    global _tracer, _trace_module
    
    if not OTEL_ENABLED:
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        
        _trace_module = trace
        
        # R: Create resource with service name
        resource = Resource.create({"service.name": "rag-corp-api"})
        
        # R: Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # R: Add console exporter (for development)
        # In production, use OTLP exporter via env vars
        exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # R: Set as global tracer provider
        trace.set_tracer_provider(provider)
        
        # R: Get tracer for this module
        _tracer = trace.get_tracer("rag-corp")
        
    except ImportError:
        pass  # OpenTelemetry not installed


# R: Initialize on module load
_init_tracing()


@contextmanager
def span(name: str, attributes: Optional[dict] = None) -> Generator[Any, None, None]:
    """
    R: Create a tracing span (no-op if tracing disabled).
    
    Usage:
        with span("embed_query", {"query_length": len(query)}):
            result = embed(query)
    
    Args:
        name: Span name (e.g., "embed_query", "search_similar")
        attributes: Optional span attributes
    
    Yields:
        Span object (or None if disabled)
    """
    if not OTEL_ENABLED or _tracer is None:
        yield None
        return
    
    with _tracer.start_as_current_span(name) as s:
        if attributes:
            for key, value in attributes.items():
                s.set_attribute(key, value)
        
        # R: Set trace/span IDs in context for log correlation
        try:
            from .context import trace_id_var, span_id_var
            span_context = s.get_span_context()
            trace_id_var.set(format(span_context.trace_id, "032x"))
            span_id_var.set(format(span_context.span_id, "016x"))
        except ImportError:
            pass
        
        yield s


def is_tracing_enabled() -> bool:
    """R: Check if tracing is enabled and initialized."""
    return OTEL_ENABLED and _tracer is not None
