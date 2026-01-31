"""
===============================================================================
ARCHIVO: mime_types.py
===============================================================================

CRC CARD (Module)
-------------------------------------------------------------------------------
Nombre:
    MIME Types y Normalización

Responsabilidades:
    - Definir constantes de MIME soportados.
    - Proveer una normalización segura del MIME (evita drift y edge cases).

Colaboradores:
    - registry.ParserRegistry
    - endpoints/handlers que validan uploads (deberían usar SUPPORTED_MIME_TYPES)
===============================================================================
"""

from __future__ import annotations

PDF_MIME: str = "application/pdf"
DOCX_MIME: str = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
TXT_MIME: str = "text/plain"

# Fuente única de verdad: todo lo que valida/decide MIME debe usar esto.
SUPPORTED_MIME_TYPES = frozenset({PDF_MIME, DOCX_MIME, TXT_MIME})


def normalize_mime_type(mime_type: str) -> str:
    """
    Normaliza el valor del MIME type.

    Por qué:
      - En producción puede llegar con mayúsculas o con parámetros:
        "Application/PDF"
        "application/pdf; charset=binary"
      - Si no normalizamos, el registry se rompe por diferencias triviales.

    Regla:
      - lower()
      - cortar en ';' y quedarse con la parte principal
      - strip()
    """
    if not mime_type:
        return ""
    return mime_type.split(";", 1)[0].strip().lower()
