"""
Name: Structured Logger Configuration

Responsibilities:
  - Configure JSON-structured logging for production readiness
  - Automatically include request context (request_id, path, method)
  - Format logs for easy parsing (Datadog, CloudWatch, etc.)
  - Include stack traces for exceptions

Collaborators:
  - context.py: Request-scoped context vars
  - Python logging module (stdlib)

Constraints:
  - No external dependencies (uses stdlib only)
  - JSON format for log aggregation compatibility
  - Never log secrets (API keys, passwords)

Notes:
  - Import as: from app.logger import logger
  - Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""

import logging
import sys
import json
import traceback
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    R: Format logs as JSON with automatic context enrichment.
    
    Includes:
      - timestamp (ISO 8601)
      - level (INFO, ERROR, etc.)
      - message
      - module, function, line
      - request_id, trace_id, span_id (from context)
      - method, path (from context)
      - exception stack trace (if present)
      - extra fields from log call
    """

    # R: Fields that should never be logged (security)
    SENSITIVE_KEYS = {"password", "api_key", "secret", "token", "authorization", "google_api_key"}

    def format(self, record: logging.LogRecord) -> str:
        # R: Build base log object
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # R: Add request context (imported lazily to avoid circular imports)
        try:
            from .context import get_context_dict
            ctx = get_context_dict()
            if ctx:
                log_obj.update(ctx)
        except ImportError:
            pass
        
        # R: Add extra fields from log call (excluding internal ones)
        internal_keys = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "taskName", "message",
        }
        
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in internal_keys:
                    # R: Filter sensitive keys
                    if key.lower() not in self.SENSITIVE_KEYS:
                        log_obj[key] = value
        
        # R: Add exception info if present
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stacktrace": traceback.format_exception(*record.exc_info),
            }
        
        return json.dumps(log_obj, default=str)


def setup_logger(name: str = "rag-api") -> logging.Logger:
    """
    R: Configure and return structured logger.
    
    Args:
        name: Logger name (default: "rag-api")
    
    Returns:
        Configured logger with JSON formatting
    """
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)

    # R: Avoid duplicate handlers on reimport
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        log.addHandler(handler)

    return log


# R: Global logger instance
logger = setup_logger()
