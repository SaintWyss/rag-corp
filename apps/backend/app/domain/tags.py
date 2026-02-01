"""
===============================================================================
TARJETA CRC — domain/tags.py
===============================================================================

Módulo:
    Normalización de Tags

Responsabilidades:
    - Normalizar `tags` desde metadata de documentos.
    - Garantizar consistencia: lista única, orden estable, sin strings vacíos.

Colaboradores:
    - use cases de ingesta: derivan tags desde metadata.

Reglas:
    - Acepta string o lista/tupla/set de strings.
    - Devuelve [] si no hay tags válidos.
===============================================================================
"""

from __future__ import annotations

from typing import Any


def normalize_tags(metadata: dict[str, Any] | None) -> list[str]:
    """Normaliza tags desde metadata."""
    if not metadata:
        return []

    raw = metadata.get("tags")
    if raw is None:
        return []

    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, (list, tuple, set)):
        candidates = list(raw)
    else:
        return []

    tags: list[str] = []
    for item in candidates:
        if not isinstance(item, str):
            continue

        cleaned = item.strip()
        if not cleaned:
            continue

        if cleaned not in tags:
            tags.append(cleaned)

    return tags
