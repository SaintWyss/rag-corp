"""
Name: User Models

Responsibilities:
  - Define user roles and user entity for authentication
  - Keep auth-specific data shapes centralized
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class UserRole(str, Enum):
    """R: Supported user roles for JWT auth."""

    ADMIN = "admin"
    EMPLOYEE = "employee"


@dataclass
class User:
    """R: User record used by authentication flows."""

    id: UUID
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime | None = None
