"""
Name: Workspace Use Case Results

Responsibilities:
  - Provide shared result/error models for workspace use cases
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from ....domain.entities import Workspace


class WorkspaceErrorCode(str, Enum):
    """R: Workspace use case error codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class WorkspaceError:
    code: WorkspaceErrorCode
    message: str


@dataclass
class WorkspaceResult:
    workspace: Workspace | None = None
    error: WorkspaceError | None = None


@dataclass
class WorkspaceListResult:
    workspaces: List[Workspace]
    error: WorkspaceError | None = None


@dataclass
class ArchiveWorkspaceResult:
    archived: bool
    error: WorkspaceError | None = None
