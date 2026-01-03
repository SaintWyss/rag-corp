"""
Name: Request Context (ContextVars)

Responsibilities:
  - Store request-scoped data (request_id, trace_id, span_id)
  - Provide async-safe context without parameter passing
  - Enable structured logging with request correlation

Collaborators:
  - middleware.py: Sets context at request start
  - logger.py: Reads context for log enrichment
  - tracing.py: Sets trace_id/span_id when OTel is enabled

Constraints:
  - Only primitive types (str) for safety
  - Default empty string (never None) for JSON serialization

Notes:
  - contextvars are async-safe (isolated per request)
  - Similar to thread-local but works with async/await
"""

from contextvars import ContextVar

# R: Request identifier (UUID) - set by middleware
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# R: OpenTelemetry trace ID (hex) - set by tracing module
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

# R: OpenTelemetry span ID (hex) - set by tracing module
span_id_var: ContextVar[str] = ContextVar("span_id", default="")

# R: HTTP method - set by middleware
http_method_var: ContextVar[str] = ContextVar("http_method", default="")

# R: Request path - set by middleware
http_path_var: ContextVar[str] = ContextVar("http_path", default="")


def get_context_dict() -> dict:
    """
    R: Get current context as dict for log enrichment.
    
    Returns:
        Dict with non-empty context values only
    """
    ctx = {}
    
    if val := request_id_var.get():
        ctx["request_id"] = val
    if val := trace_id_var.get():
        ctx["trace_id"] = val
    if val := span_id_var.get():
        ctx["span_id"] = val
    if val := http_method_var.get():
        ctx["method"] = val
    if val := http_path_var.get():
        ctx["path"] = val
    
    return ctx


def clear_context() -> None:
    """R: Reset all context vars (called at request end)."""
    request_id_var.set("")
    trace_id_var.set("")
    span_id_var.set("")
    http_method_var.set("")
    http_path_var.set("")
