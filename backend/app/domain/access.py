"""
Name: Access Normalization

Responsibilities:
  - Normalize allowed_roles payloads for document ACL
"""

from __future__ import annotations

from typing import Any

from ..identity.users import UserRole


_VALID_ROLES = {role.value for role in UserRole}


def normalize_allowed_roles(metadata: dict[str, Any] | None) -> list[str]:
    if not metadata:
        return []

    raw = metadata.get("allowed_roles")
    if raw is None:
        return []

    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = raw
    else:
        return []

    roles: list[str] = []
    for item in candidates:
        if not isinstance(item, str):
            continue
        cleaned = item.strip().lower()
        if cleaned in _VALID_ROLES and cleaned not in roles:
            roles.append(cleaned)
    return roles
