# =============================================================================
# FILE: application/context_builder.py
# =============================================================================
"""
===============================================================================
SERVICE: Context Builder (RAG Grounding Assembler)
===============================================================================

Name:
    Context Builder (RAG Grounding Assembler)

Qué es:
    Construye el string de CONTEXTO que se inyecta al LLM para RAG, incluyendo:
      - delimitadores claros por chunk ([S#]) para grounding
      - metadata por chunk para trazabilidad (doc_id, chunk_id, fragmento, source)
      - sección final "FUENTES" que mapea [S#] → metadata (contrato de citas)
      - mitigación best-effort contra prompt-injection (marcado de contenido sospechoso)
      - límite estricto de tamaño total (max_size) incluyendo "FUENTES"

Arquitectura:
    - Estilo: Clean Architecture / Hexagonal
    - Capa: Application (servicio de ensamblado para input del LLM)
    - Rol: Assembler/Builder (prepara datos del dominio para el adaptador LLM)

Patrones:
    - Builder/Assembler: arma representación textual compuesta a partir de Chunk.
    - Strategy: size_counter inyectable (chars vs tokens).
    - Policy: aplica límites y sanitización.
    - Determinismo: preserva orden de ranking y dedupe estable.

SOLID:
    - SRP: solo arma contexto (no retrieval, no LLM).
    - OCP: se puede extender formateo/políticas sin romper consumidores.
    - DIP: depende de entidades del dominio (Chunk), no de proveedores externos.
    - OCP: size_counter inyectable permite integrar tiktoken sin cambiar la clase.

CRC (Class-Responsibility-Collaboration):
    Class: ContextBuilder
    Responsibilities:
      - Deduplicar chunks con clave estable
      - Formatear chunks con [S#] + metadata + delimitadores robustos
      - Sanitizar contenido para evitar colisión con delimitadores
      - Marcar contenido riesgoso según policy
      - Construir "FUENTES" alineado a [S#]
      - Respetar max_size usando el counter inyectado
    Collaborators:
      - domain.entities.Chunk
      - size_counter (función inyectable)
===============================================================================
"""

from __future__ import annotations

import re
from typing import Callable, Final, Hashable, List, Protocol, Sequence, Set

from ..crosscutting.logger import logger
from ..domain.entities import Chunk

# -----------------------------------------------------------------------------
# Type Aliases
# -----------------------------------------------------------------------------
SizeCounter = Callable[[str], int]


class TokenCounter(Protocol):
    """
    Protocol para contadores de tokens (future-proofing).

    Permite inyectar tiktoken.encode o similar cuando se integre con modelos reales.
    """

    def __call__(self, text: str) -> int: ...


# -----------------------------------------------------------------------------
# Delimitadores (contrato de citas: [S#])
# -----------------------------------------------------------------------------
CHUNK_DELIMITER: Final[str] = "\n---[S{index}]---\n"
CHUNK_END: Final[str] = "\n---[FIN S{index}]---\n"
SOURCES_HEADER: Final[str] = "\nFUENTES:\n"

# -----------------------------------------------------------------------------
# Anti prompt-injection (best-effort)
# -----------------------------------------------------------------------------
_SUSPICIOUS_PATTERNS = (
    r"ignora (todas )?las instrucciones",
    r"ignore (all )?previous instructions",
    r"olvida las reglas",
    r"act(ú|u)a como",
    r"you are now",
    r"sos el system",
    r"system prompt",
    r"developer message",
    r"revela (tu|el) prompt",
    r"api key",
    r"clave",
    r"secret",
)
_SUSPICIOUS_RE: Final[re.Pattern[str]] = re.compile(
    "|".join(_SUSPICIOUS_PATTERNS), flags=re.IGNORECASE
)

# Colisión con delimitadores
_DELIMITER_COLLISION_RE: Final[re.Pattern[str]] = re.compile(
    r"---\[(FIN )?S\d+\]---", flags=re.IGNORECASE
)


# -----------------------------------------------------------------------------
# Default size counter (caracteres)
# -----------------------------------------------------------------------------
def _default_char_counter(text: str) -> int:
    """
    Contador por defecto: caracteres.

    Nota:
        - Para integrar con LLMs reales, inyectar tiktoken.encode o similar.
        - Aproximación conservadora: 1 token ~= 4 chars (no usada aquí, solo len).
    """
    return len(text)


# -----------------------------------------------------------------------------
# Helpers de sanitización
# -----------------------------------------------------------------------------
def _escape_delimiters(text: str) -> str:
    """Neutraliza tokens que colisionan con delimitadores del contexto."""
    if not text:
        return text
    return _DELIMITER_COLLISION_RE.sub(lambda m: m.group(0).replace("---", "—"), text)


def _mark_suspicious_content(text: str) -> str:
    """Marca contenido sospechoso de prompt-injection (sin borrar)."""
    if not text:
        return text
    if _SUSPICIOUS_RE.search(text):
        return "[Contenido sospechoso filtrado]\n" + text
    return text


def _sanitize_chunk_content(raw: str) -> str:
    """Pipeline de sanitización: escape + marcado."""
    text = raw or ""
    text = _escape_delimiters(text)
    text = _mark_suspicious_content(text)
    return text


# -----------------------------------------------------------------------------
# Formateo de chunks
# -----------------------------------------------------------------------------
def _format_chunk_metadata(chunk: Chunk) -> str:
    """Construye metadata legible para grounding (una línea)."""
    parts: List[str] = []

    if getattr(chunk, "document_title", None):
        parts.append(f"Título: {chunk.document_title}")
    if getattr(chunk, "document_id", None):
        parts.append(f"Doc ID: {chunk.document_id}")
    if getattr(chunk, "chunk_id", None):
        parts.append(f"Chunk ID: {chunk.chunk_id}")
    if getattr(chunk, "chunk_index", None) is not None:
        parts.append(f"Fragmento: {chunk.chunk_index + 1}")
    if getattr(chunk, "document_source", None):
        parts.append(f"Source: {chunk.document_source}")

    return " | ".join(parts).strip()


def _format_chunk(chunk: Chunk, index: int) -> str:
    """Formatea un chunk completo con delimitadores, metadata y contenido sanitizado."""
    header = CHUNK_DELIMITER.format(index=index)
    footer = CHUNK_END.format(index=index)

    metadata_line = _format_chunk_metadata(chunk)
    safe_content = _sanitize_chunk_content(getattr(chunk, "content", "") or "")

    if metadata_line:
        return f"{header}[{metadata_line}]\n{safe_content}{footer}"
    return f"{header}{safe_content}{footer}"


def _format_source_line(chunk: Chunk, index: int) -> str:
    """Devuelve una línea de FUENTES alineada con [S#]."""
    parts: List[str] = []
    if getattr(chunk, "document_title", None):
        parts.append(f"doc_title={chunk.document_title}")
    if getattr(chunk, "document_id", None):
        parts.append(f"doc_id={chunk.document_id}")
    if getattr(chunk, "chunk_id", None):
        parts.append(f"chunk_id={chunk.chunk_id}")
    if getattr(chunk, "chunk_index", None) is not None:
        parts.append(f"fragmento={chunk.chunk_index + 1}")
    if getattr(chunk, "document_source", None):
        parts.append(f"source={chunk.document_source}")

    metadata = " | ".join(parts).strip()
    return f"[S{index}] {metadata}".rstrip()


# -----------------------------------------------------------------------------
# Deduplicación
# -----------------------------------------------------------------------------
def _dedupe_key(chunk: Chunk) -> Hashable:
    """Clave de deduplicación estable."""
    cid = getattr(chunk, "chunk_id", None)
    if cid is not None:
        return ("chunk_id", str(cid))

    doc_id = getattr(chunk, "document_id", None)
    chunk_index = getattr(chunk, "chunk_index", None)
    if doc_id is not None and chunk_index is not None:
        return ("doc_chunk_index", str(doc_id), int(chunk_index))

    content = getattr(chunk, "content", "") or ""
    if doc_id is not None:
        return ("doc_content_hash", str(doc_id), hash(content))

    return ("content_hash", hash(content))


# -----------------------------------------------------------------------------
# ContextBuilder
# -----------------------------------------------------------------------------
class ContextBuilder:
    """
    Builder de contexto para RAG.

    Garantías:
      - Incluye "FUENTES" dentro del límite max_size.
      - Alineación 1:1 de índices [S#] entre chunks y fuentes.
      - No reordena chunks (preserva ranking de entrada).

    Args:
        max_size: Límite máximo (en unidades del size_counter).
        size_counter: Función str->int para medir tamaño.
                      Por defecto: len() (caracteres).
                      Para tokens reales: inyectar tiktoken.encode.
    """

    def __init__(
        self,
        max_size: int = 12000,
        size_counter: SizeCounter | None = None,
    ) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        self._max_size = max_size
        self._counter = size_counter or _default_char_counter

    @property
    def max_size(self) -> int:
        """Límite configurado (read-only)."""
        return self._max_size

    def build(self, chunks: Sequence[Chunk]) -> tuple[str, int]:
        """
        Construye el contexto final.

        Args:
            chunks: chunks ya rankeados por similitud (orden preservado)

        Returns:
            (context_string, chunks_used)
        """
        if not chunks:
            return "", 0

        # Deduplicación estable preservando orden
        unique_chunks: List[Chunk] = []
        seen: Set[Hashable] = set()
        for chunk in chunks:
            key = _dedupe_key(chunk)
            if key in seen:
                continue
            seen.add(key)
            unique_chunks.append(chunk)

        # Armado incremental con límite estricto
        context_parts: List[str] = []
        source_lines: List[str] = []

        context_size = 0
        sources_size = self._counter(SOURCES_HEADER)

        chunks_used = 0

        for i, chunk in enumerate(unique_chunks, start=1):
            formatted_chunk = _format_chunk(chunk, i)
            formatted_source = _format_source_line(chunk, i) + "\n"

            chunk_cost = self._counter(formatted_chunk)
            source_cost = self._counter(formatted_source)

            prospective_total = context_size + chunk_cost + sources_size + source_cost

            if prospective_total > self._max_size:
                logger.debug(
                    "Context truncated to respect max_size",
                    extra={
                        "max_size": self._max_size,
                        "chunks_used": chunks_used,
                        "current_size": context_size + sources_size,
                    },
                )
                break

            context_parts.append(formatted_chunk)
            source_lines.append(formatted_source.rstrip())

            context_size += chunk_cost
            sources_size += source_cost
            chunks_used += 1

        if chunks_used == 0:
            return "", 0

        context = "".join(context_parts)
        context += SOURCES_HEADER + "\n".join(source_lines) + "\n"

        logger.debug(
            "Built context",
            extra={
                "chunks_used": chunks_used,
                "context_size": self._counter(context),
                "max_size": self._max_size,
            },
        )

        return context, chunks_used


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
def get_context_builder(
    size_counter: SizeCounter | None = None,
) -> ContextBuilder:
    """
    Factory usando settings.

    Args:
        size_counter: Opcional. Si se pasa, se usa en lugar del default (len).

    Nota:
        - El composition root puede inyectar tiktoken aquí.
    """
    from ..crosscutting.config import get_settings

    settings = get_settings()
    return ContextBuilder(
        max_size=settings.max_context_chars,
        size_counter=size_counter,
    )
