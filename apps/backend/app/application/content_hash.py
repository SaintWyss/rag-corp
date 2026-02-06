"""
===============================================================================
MÓDULO: Content Hash — Utilidades de normalización y hash para deduplicación
===============================================================================

Responsabilidades:
  - Normalizar texto para hashing determinístico (NFC, trim, collapse whitespace).
  - Computar SHA-256 sobre contenido normalizado, scopeado por workspace.
  - Computar SHA-256 sobre bytes crudos de archivo, scopeado por workspace.

Colaboradores:
  - application/usecases/ingestion: consume compute_content_hash y compute_file_hash
  - domain/entities.Document: almacena el hash resultante (content_hash)

Decisiones de diseño:
  - Funciones puras (sin IO, sin side effects).
  - NFC unicode (canonical decomposition + canonical composition).
  - NO lowercase: preserva case original para hash fiel al contenido.
  - Whitespace collapse: normaliza tabs, newlines, espacios múltiples a un solo espacio.
  - Scoping por workspace_id: mismo contenido en distintos workspaces = distinto hash.
===============================================================================
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from uuid import UUID


def normalize_text(text: str) -> str:
    """
    Normaliza texto para hashing determinístico.

    Pasos:
      1. NFC unicode (canonical form C).
      2. Strip leading/trailing whitespace.
      3. Collapse whitespace interno (tabs, newlines, espacios múltiples → 1 espacio).

    NO aplica lowercase (se preserva case original).
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def compute_content_hash(workspace_id: UUID, content: str) -> str:
    """
    SHA-256 sobre workspace_id + contenido de texto normalizado.

    Formato del payload: "{workspace_id}:{normalized_content}"
    Retorna: hex digest de 64 caracteres.
    """
    normalized = normalize_text(content)
    payload = f"{workspace_id}:{normalized}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_file_hash(workspace_id: UUID, file_bytes: bytes) -> str:
    """
    SHA-256 sobre workspace_id + bytes crudos del archivo.

    No aplica normalización de texto (los bytes son determinísticos).
    Retorna: hex digest de 64 caracteres.
    """
    h = hashlib.sha256()
    h.update(str(workspace_id).encode("utf-8"))
    h.update(b":")
    h.update(file_bytes)
    return h.hexdigest()
