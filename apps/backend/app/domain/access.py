"""
===============================================================================
TARJETA CRC — domain/access.py
===============================================================================

Módulo:
    Normalización de Acceso (allowed_roles)

Responsabilidades:
    - Normalizar el payload `allowed_roles` proveniente de metadata.
    - Garantizar semántica consistente (lista única, orden estable, lower-case).
    - Validar contra roles conocidos del sistema.

Colaboradores:
    - identity.users.UserRole: catálogo de roles válidos (admin/employee).
    - use cases de ingesta: derivan allowed_roles desde metadata.

Notas:
    - Este helper es puro: no toca DB ni infraestructura.
    - Si `allowed_roles` no existe o es inválido, devuelve [] (sin restricciones).
===============================================================================
"""

from __future__ import annotations

from typing import Any

from ..identity.users import UserRole

_VALID_ROLES: set[str] = {role.value for role in UserRole}


def normalize_allowed_roles(metadata: dict[str, Any] | None) -> list[str]:
    """
    Normaliza allowed_roles desde metadata.

    Formatos aceptados:
      - {"allowed_roles": "admin"}
      - {"allowed_roles": ["admin", "employee"]}
      - {"allowed_roles": ("admin", ...)}  (tuplas/sets también)

    Regla:
      - Devuelve lista sin duplicados, en orden de aparición.
      - Cada rol se normaliza: strip + lower.
      - Se filtran roles no reconocidos.
    """
    if not metadata:
        return []

    raw = metadata.get("allowed_roles")
    if raw is None:
        return []

    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, (list, tuple, set)):
        candidates = list(raw)
    else:
        return []

    roles: list[str] = []
    for item in candidates:
        if not isinstance(item, str):
            continue

        cleaned = item.strip().lower()
        if not cleaned:
            continue

        if cleaned not in _VALID_ROLES:
            continue

        if cleaned not in roles:
            roles.append(cleaned)

    return roles
