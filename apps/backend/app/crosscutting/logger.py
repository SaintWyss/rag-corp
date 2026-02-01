# apps/backend/app/crosscutting/logger.py
"""
===============================================================================
MÓDULO: Logger estructurado (JSON) con contexto de request
===============================================================================

Objetivo
--------
Loguear de forma:
- Parseable (JSON)
- Correlacionable (request_id / trace_id / span_id)
- Segura (redacción de secretos)
- Con bajo overhead

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  JSONFormatter + setup_logger()

Responsabilidades:
  - Formatear logs como JSON
  - Enriquecer con contexto (request_id, path, method, trace_id, span_id)
  - Redactar campos sensibles y limitar tamaños

Colaboradores:
  - app/context.py (ContextVars)
  - crosscutting/config.py (nivel y formato)
===============================================================================
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

# Campos internos del LogRecord que NO queremos copiar como "extra".
_INTERNAL_LOGRECORD_KEYS: set[str] = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "taskName",
}


class _Redactor:
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      _Redactor

    Responsabilidades:
      - Redactar claves sensibles
      - Recortar strings gigantes
      - Mantener serialización segura en JSON

    Colaboradores:
      - JSONFormatter
    ----------------------------------------------------------------------------
    """

    # Claves “probables” de secretos
    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "x-api-key",
        "access_token",
        "refresh_token",
        "private_key",
        "credential",
        "google_api_key",
        "s3_secret_key",
    }

    def __init__(self, max_str: int = 8_000, max_depth: int = 4):
        self._max_str = max_str
        self._max_depth = max_depth

    def sanitize(self, value: Any, *, depth: int = 0, key: str | None = None) -> Any:
        # Regla 1: si la clave es sensible, redactar
        if key and key.lower() in self.SENSITIVE_KEYS:
            return "***REDACTADO***"

        # Regla 2: depth limit para evitar logs monstruosos
        if depth > self._max_depth:
            return "***TRUNCADO***"

        # Strings: recorte
        if isinstance(value, str):
            if len(value) <= self._max_str:
                return value
            return value[: self._max_str] + "…(truncado)"

        # Bytes: no los volcamos
        if isinstance(value, (bytes, bytearray)):
            return f"<bytes {len(value)}B>"

        # Dict: recurse
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                try:
                    ks = str(k)
                except Exception:
                    ks = "<key>"
                out[ks] = self.sanitize(v, depth=depth + 1, key=ks)
            return out

        # List/Tuple
        if isinstance(value, (list, tuple)):
            return [self.sanitize(v, depth=depth + 1, key=key) for v in value]

        # Fallback: intentar serializar “as is”, sino str()
        try:
            json.dumps(value, default=str)
            return value
        except Exception:
            return str(value)


class JSONFormatter(logging.Formatter):
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      JSONFormatter

    Responsabilidades:
      - Convertir LogRecord -> JSON
      - Enriquecer con contexto de request
      - Adjuntar stacktrace cuando hay excepción

    Colaboradores:
      - app/context.get_context_dict()
      - _Redactor
    ----------------------------------------------------------------------------
    """

    def __init__(self):
        super().__init__()
        self._redactor = _Redactor()

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pid": os.getpid(),
        }

        # Contexto de request (si existe)
        try:
            from ..context import get_context_dict

            ctx = get_context_dict()
            if ctx:
                payload.update(ctx)
        except Exception:
            # No romper logging si el contexto no está disponible
            pass

        # Extra fields: todo lo que venga en record.__dict__ que no sea interno
        for k, v in record.__dict__.items():
            if k in _INTERNAL_LOGRECORD_KEYS:
                continue
            payload[k] = self._redactor.sanitize(v, key=k)

        # Excepciones: stacktrace completo (pero serializable)
        if record.exc_info:
            exc_type = record.exc_info[0].__name__ if record.exc_info[0] else None
            exc_msg = str(record.exc_info[1]) if record.exc_info[1] else None
            payload["exception"] = {
                "type": exc_type,
                "message": exc_msg,
                "stacktrace": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(
            payload, ensure_ascii=False, default=str, separators=(",", ":")
        )


def setup_logger(name: str = "rag-api") -> logging.Logger:
    """
    Crea y configura el logger global.

    - Evita duplicación de handlers en reimport
    - Respeta log_level / log_json desde Settings cuando estén disponibles
    """
    log = logging.getLogger(name)

    # Default seguro
    level = "INFO"
    use_json = True

    # Tomar settings sin provocar ciclos fuertes (best-effort)
    try:
        from .config import get_settings

        s = get_settings()
        level = (s.log_level or "INFO").upper()
        use_json = bool(getattr(s, "log_json", True))
    except Exception:
        pass

    log.setLevel(getattr(logging, level, logging.INFO))

    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            JSONFormatter()
            if use_json
            else logging.Formatter("%(levelname)s %(message)s")
        )
        log.addHandler(handler)

    return log


# Instancia global (import-friendly)
logger = setup_logger()
