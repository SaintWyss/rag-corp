"""
===============================================================================
TARJETA CRC — identity/users.py
===============================================================================

Módulo:
    Modelos de Usuario (JWT)

Responsabilidades:
    - Definir el enum de roles de usuario para autenticación/autorización.
    - Definir el dataclass User utilizado por los flujos de auth (login / token).
    - Mantener el contrato de datos de auth centralizado y estable.

Colaboradores:
    - identity/auth_users.py: usa User y UserRole para emitir/validar JWT.
    - infrastructure/repositories/postgres/user.py: mapea filas -> User.
    - identity/dual_auth.py: construye principal de tipo USER.

Notas (Clean Code / Sustentabilidad):
    - Este módulo NO contiene lógica de negocio: solo “shapes” de datos.
    - Si agregás nuevos roles, revisá dependencias require_roles / require_user_roles.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class UserRole(str, Enum):
    """Roles soportados para autenticación JWT."""

    ADMIN = "admin"
    EMPLOYEE = "employee"


@dataclass(frozen=True, slots=True)
class User:
    """Registro de usuario utilizado por autenticación (JWT)."""

    id: UUID
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime | None = None
