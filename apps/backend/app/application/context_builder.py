"""
Name: Context Builder (RAG Grounding Assembler)

Qué es
------
Construye el string de CONTEXTO que se inyecta al LLM para RAG, incluyendo:
  - delimitadores claros por chunk ([S#]) para grounding
  - metadata por chunk para trazabilidad (doc_id, chunk_id, fragmento, source)
  - sección final "FUENTES" que mapea [S#] → metadata (contrato de citas)
  - mitigación básica contra prompt-injection (marcado/filtrado de contenido sospechoso)
  - límite estricto de tamaño total (MAX_CONTEXT_CHARS) incluyendo "FUENTES"

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Application (servicio de orquestación para construir input del LLM)
- Rol: “Assembler” / “Presenter” del contexto (prepara datos del dominio para el adaptador LLM)

Patrones
--------
- Assembler / Builder: arma una representación textual compuesta a partir de entidades (Chunk)
- Policy: aplica políticas de seguridad (anti-injection) y límites de tamaño
- Determinismo: preserva orden (ya viene rankeado por similitud), dedupe estable

SOLID
-----
- SRP: solo arma el contexto (no hace retrieval, no llama LLM).
- OCP: se puede extender el formateo o políticas sin tocar consumidores.
- DIP: depende de entidades del dominio (Chunk), no de proveedores externos.

CRC (Class-Responsibility-Collaboration)
----------------------------------------
Class: ContextBuilder
Responsibilities:
  - Deduplicar chunks (chunk_id o clave compuesta)
  - Formatear chunks con [S#] + metadata + delimitadores robustos
  - Aplicar anti-injection (escape + marcado de contenido sospechoso)
  - Construir "FUENTES" alineado a [S#]
  - Respetar max_chars incluyendo la sección de fuentes
Collaborators:
  - domain.entities.Chunk
  - config (max_context_chars)
Constraints:
  - El contexto es INPUT NO CONFIABLE (treat as data)
  - Nunca permitir que texto de chunks rompa los límites/delimitadores
  - Mantener alineación 1:1 entre indices [S#] en chunks y en FUENTES
"""

from __future__ import annotations

import re
from typing import Hashable, List, Optional, Set, Tuple

from ..crosscutting.logger import logger
from ..domain.entities import Chunk

# ---------------------------------------------------------------------------
# Delimitadores “duros” (señales visibles para el modelo y difíciles de falsificar)
# ---------------------------------------------------------------------------
# R: Mantengo tu formato [S#] porque el contrato exige citas [S#].
CHUNK_DELIMITER = "\n---[S{index}]---\n"
CHUNK_END = "\n---[FIN S{index}]---\n"

# R: Sección de fuentes: el contrato pide que exista y mapee [S#] → metadata.
SOURCES_HEADER = "\nFUENTES:\n"


# ---------------------------------------------------------------------------
# Anti prompt-injection (best-effort, sin destruir evidencia útil)
# ---------------------------------------------------------------------------
# R: Detecta frases típicas de inyección. No es “seguridad perfecta”, pero reduce riesgo.
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
_SUSPICIOUS_RE = re.compile("|".join(_SUSPICIOUS_PATTERNS), flags=re.IGNORECASE)


# R: Detecta colisión con tus delimitadores exactos (para evitar que el contenido “rompa” el contexto).
#    Ej: un chunk que contenga literalmente '---[S1]---' podría confundir.
_DELIMITER_COLLISION_RE = re.compile(r"---\[(FIN )?S\d+\]---", flags=re.IGNORECASE)


def _escape_delimiters(text: str) -> str:
    """
    R: Mitiga colisiones con delimitadores del contexto.

    Estrategia:
      - Reemplaza cualquier token que matchee la forma '---[S#]---' o '---[FIN S#]---'
        por una variante con guión largo (—) para que NO sea interpretado como boundary.
    """
    if not text:
        return text
    return _DELIMITER_COLLISION_RE.sub(lambda m: m.group(0).replace("---", "—"), text)


def _mark_suspicious_content(text: str) -> str:
    """
    R: Marca (sin borrar totalmente) contenido sospechoso de prompt-injection.

    Política:
      - Si detectamos patrones fuertes, insertamos una marca visible.
      - No eliminamos todo el chunk para no perder evidencia útil, pero dejamos trazabilidad.
    """
    if not text:
        return text
    if _SUSPICIOUS_RE.search(text):
        # R: Coincide con tu prompt v2: reportar "[Contenido sospechoso filtrado]"
        return "[Contenido sospechoso filtrado]\n" + text
    return text


def _sanitize_chunk_content(raw: str) -> str:
    """
    R: Pipeline de sanitización del contenido del chunk.

    Orden:
      1) escape delimitadores (evita “romper” boundaries)
      2) marcar contenido sospechoso (anti-injection)
    """
    text = raw or ""
    text = _escape_delimiters(text)
    text = _mark_suspicious_content(text)
    return text


def _format_chunk_metadata(chunk: Chunk) -> str:
    """
    R: Construye metadata legible para grounding.

    Nota:
      - Esto aparece arriba del contenido del chunk para ayudar al LLM a “anclar”.
    """
    parts: List[str] = []

    if getattr(chunk, "document_title", None):
        parts.append(f"Título: {chunk.document_title}")

    if getattr(chunk, "document_id", None):
        parts.append(f"Doc ID: {chunk.document_id}")

    if getattr(chunk, "chunk_id", None):
        parts.append(f"Chunk ID: {chunk.chunk_id}")

    if getattr(chunk, "chunk_index", None) is not None:
        # R: chunk_index suele ser 0-based, mostramos 1-based
        parts.append(f"Fragmento: {chunk.chunk_index + 1}")

    if getattr(chunk, "document_source", None):
        parts.append(f"Source: {chunk.document_source}")

    return " | ".join(parts).strip()


def _format_chunk(chunk: Chunk, index: int) -> str:
    """
    R: Formatea un chunk completo con delimitadores, metadata y contenido sanitizado.

    Args:
        chunk: entidad Chunk
        index: índice 1-based usado para citas [S#]
    """
    header = CHUNK_DELIMITER.format(index=index)
    footer = CHUNK_END.format(index=index)

    metadata_line = _format_chunk_metadata(chunk)
    safe_content = _sanitize_chunk_content(getattr(chunk, "content", "") or "")

    if metadata_line:
        return f"{header}[{metadata_line}]\n{safe_content}{footer}"
    return f"{header}{safe_content}{footer}"


def _format_source_line(chunk: Chunk, index: int) -> str:
    """
    R: Devuelve una línea de FUENTES alineada con [S#] (contrato).

    El contrato exige: sección final "Fuentes" con mapeo [S#] → metadata.
    """
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


def _dedupe_key(chunk: Chunk) -> Hashable:
    """
    R: Clave de deduplicación estable.

    Preferimos:
      1) chunk_id (si existe)
      2) doc_id + chunk_index (si existe)
      3) fallback: doc_id + hash del contenido (último recurso)
    """
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


class ContextBuilder:
    """
    R: Build context string from chunks with grounding metadata.

    Diseño:
      - Incluye "FUENTES" dentro del límite max_chars (estricto).
      - Mantiene alineación exacta entre índices de chunks y líneas de fuentes.
    """

    def __init__(self, max_chars: int = 12000):
        if max_chars <= 0:
            raise ValueError("max_chars must be > 0")
        self.max_chars = max_chars

    def build(self, chunks: List[Chunk]) -> tuple[str, int]:
        """
        R: Construye el contexto final.

        Args:
            chunks: chunks ya rankeados por similitud (orden preservado)

        Returns:
            (context_string, chunks_used)
        """
        if not chunks:
            return "", 0

        # R: Deduplicación estable preservando el orden de llegada
        seen: Set[Hashable] = set()
        unique_chunks: List[Chunk] = []
        for chunk in chunks:
            key = _dedupe_key(chunk)
            if key in seen:
                continue
            seen.add(key)
            unique_chunks.append(chunk)

        # R: Armado incremental con límite estricto incluyendo FUENTES
        context_parts: List[str] = []
        source_lines: List[str] = []

        # R: Estos contadores permiten calcular tamaño sin reconstruir todo cada vez.
        context_chars = 0
        sources_chars = len(SOURCES_HEADER)  # R: overhead fijo si hay al menos 1 fuente

        chunks_used = 0

        for i, chunk in enumerate(unique_chunks, start=1):
            formatted_chunk = _format_chunk(chunk, i)
            formatted_source = _format_source_line(chunk, i)

            # R: Tamaño “prospectivo” si agregamos este chunk + su línea de fuente.
            #     - +1 por newline de fuentes al join
            prospective_context = context_chars + len(formatted_chunk)
            prospective_sources = sources_chars + len(formatted_source) + 1

            # R: Si no hay ningún chunk aún, sources header cuenta; si no agregamos nada, FUENTES no se agrega.
            prospective_total = prospective_context + prospective_sources

            if prospective_total > self.max_chars:
                logger.debug(
                    "Context truncated to respect max_chars",
                    extra={
                        "max_chars": self.max_chars,
                        "chunks_used": chunks_used,
                        "context_chars": context_chars,
                        "sources_chars": sources_chars,
                    },
                )
                break

            context_parts.append(formatted_chunk)
            source_lines.append(formatted_source)

            context_chars = prospective_context
            sources_chars = prospective_sources
            chunks_used += 1

        if chunks_used == 0:
            # R: Nada entra en el límite; devolvemos vacío para que el LLMService aplique fallback contractual.
            return "", 0

        # R: Construcción final: chunks + FUENTES (alineado con [S#])
        context = "".join(context_parts)
        context += SOURCES_HEADER + "\n".join(source_lines) + "\n"

        logger.debug(
            "Built context",
            extra={
                "chunks_used": chunks_used,
                "context_chars": len(context),
                "max_chars": self.max_chars,
            },
        )

        return context, chunks_used


def get_context_builder() -> ContextBuilder:
    """
    R: Factory (composition helper) usando settings.

    Nota:
      - Idealmente, el composition root inyecta este builder a Infra (DIP).
    """
    from ..crosscutting.config import get_settings

    settings = get_settings()
    return ContextBuilder(max_chars=settings.max_context_chars)
