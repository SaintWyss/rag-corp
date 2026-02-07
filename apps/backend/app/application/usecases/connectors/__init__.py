"""
===============================================================================
CONNECTOR USE CASES: Results & Errors
===============================================================================

DTOs de resultado y error para los use cases de connectors.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from app.domain.connectors import ConnectorSource


class ConnectorErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    FORBIDDEN = "FORBIDDEN"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


@dataclass(frozen=True)
class ConnectorError:
    code: ConnectorErrorCode
    message: str


@dataclass
class ConnectorSourceResult:
    source: Optional[ConnectorSource] = None
    error: Optional[ConnectorError] = None


@dataclass
class ConnectorSourceListResult:
    sources: List[ConnectorSource]
    error: Optional[ConnectorError] = None


@dataclass
class ConnectorDeleteResult:
    deleted: bool = False
    error: Optional[ConnectorError] = None
