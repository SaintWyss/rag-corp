"""
Name: Structured Logger Configuration

Responsibilities:
  - Configure JSON-structured logging for production readiness
  - Provide consistent logger instance across application
  - Format logs for easy parsing (Datadog, CloudWatch, etc.)

Collaborators:
  - Python logging module (stdlib)
  - All modules that need logging

Constraints:
  - No external dependencies (uses stdlib only)
  - JSON format for log aggregation compatibility

Notes:
  - Import as: from app.logger import logger
  - Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""
import logging
import sys
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logger(name: str = "rag-api") -> logging.Logger:
    """Configure and return structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logger()
