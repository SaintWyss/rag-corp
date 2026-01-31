# =============================================================================
# FILE: application/query_rewriter.py
# =============================================================================
"""
===============================================================================
QUERY REWRITER (RAG Enhancement)
===============================================================================

Name:
    Query Rewriter

Business Goal:
    Mejora la precisión del RAG reescribiendo queries ambiguos o incompletos
    antes de la búsqueda vectorial. Esto es especialmente útil cuando:
      - El usuario hace preguntas de seguimiento ("¿y eso aplica a mi caso?")
      - La query es muy corta o genérica ("vacaciones")
      - Hay pronombres sin antecedente claro ("¿qué pasa con él?")

Why (Context / Intención):
    - La búsqueda vectorial es literal: no "entiende" contexto conversacional.
    - Sin rewriting, "¿y eso?" no matchea nada útil.
    - Con rewriting, "¿y eso?" → "¿La política de vacaciones aplica también
      a empleados part-time?" que sí matchea chunks relevantes.

Estrategia:
    1) Analizar si la query necesita rewriting (es corta, tiene pronombres, etc.)
    2) Si sí, usar el historial conversacional para expandir/clarificar
    3) Retornar la query reescrita (o la original si no necesita cambios)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    QueryRewriter

Responsibilities:
    - Detectar queries que se beneficiarían de rewriting.
    - Usar LLM para generar versión mejorada de la query.
    - Preservar la intención original del usuario.
    - Fallback a query original si el rewriting falla.

Collaborators:
    - LLMService: Generación de la query reescrita.
    - ConversationMessage: Contexto del historial.
===============================================================================
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final, List, Optional, Protocol

from ..domain.entities import ConversationMessage

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_MIN_QUERY_LENGTH_FOR_SKIP: Final[int] = 50  # Queries largas probablemente son claras
_MAX_QUERY_LENGTH: Final[int] = 500  # Límite para evitar queries gigantes

# Patrones que indican que la query necesita contexto
_CONTEXT_NEEDED_PATTERNS: Final[List[re.Pattern]] = [
    re.compile(r"\b(eso|esto|él|ella|ellos|ellas|lo|la|los|las)\b", re.IGNORECASE),
    re.compile(r"\b(anterior|previo|mencionado|dicho)\b", re.IGNORECASE),
    re.compile(r"^\s*(y|pero|entonces|además|también)\s+", re.IGNORECASE),
    re.compile(r"\?$"),  # Preguntas muy cortas
]

# Prompt template para rewriting
_REWRITE_PROMPT_TEMPLATE: Final[
    str
] = """Eres un asistente que mejora consultas para búsqueda semántica.

Tu tarea es reescribir la CONSULTA ACTUAL del usuario para que sea más clara y completa,
usando el contexto del historial si es necesario.

Reglas:
1. Si la consulta es clara y completa, devuélvela sin cambios.
2. Si tiene pronombres ambiguos (eso, esto, él, etc.), reemplázalos con términos concretos del historial.
3. Si es una pregunta de seguimiento, incluye el tema de la conversación.
4. Mantén el idioma original de la consulta.
5. No agregues información que el usuario no pidió.
6. La respuesta debe ser SOLO la consulta reescrita, sin explicaciones.

HISTORIAL RECIENTE:
{history}

CONSULTA ACTUAL:
{query}

CONSULTA REESCRITA:"""


# -----------------------------------------------------------------------------
# Ports (Protocols)
# -----------------------------------------------------------------------------
class LLMRewriterPort(Protocol):
    """Port minimalista para el LLM usado en rewriting."""

    def generate_text(self, prompt: str, max_tokens: int = 200) -> str:
        """Genera texto a partir de un prompt."""
        ...


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RewriteResult:
    """
    Resultado del proceso de rewriting.

    Attributes:
        original_query: La query original del usuario.
        rewritten_query: La query reescrita (o igual a original si no se reescribió).
        was_rewritten: True si se aplicó rewriting.
        reason: Razón del rewriting (o "skipped" si no se hizo).
    """

    original_query: str
    rewritten_query: str
    was_rewritten: bool = False
    reason: str = "skipped"


# -----------------------------------------------------------------------------
# Query Rewriter
# -----------------------------------------------------------------------------
class QueryRewriter:
    """
    Servicio de rewriting de queries para mejorar precisión de RAG.

    Uso típico:
        rewriter = QueryRewriter(llm_service)
        result = rewriter.rewrite(query, history)
        search_query = result.rewritten_query  # Usar para retrieval
    """

    def __init__(
        self,
        llm_service: LLMRewriterPort,
        *,
        enabled: bool = True,
        min_history_messages: int = 1,
    ) -> None:
        """
        Args:
            llm_service: Servicio LLM para generar la reescritura.
            enabled: Si False, siempre retorna la query original.
            min_history_messages: Mínimo de mensajes de historial para activar rewriting.
        """
        self._llm = llm_service
        self._enabled = enabled
        self._min_history = min_history_messages

    def rewrite(
        self,
        query: str,
        history: Optional[List[ConversationMessage]] = None,
    ) -> RewriteResult:
        """
        Reescribe una query si se beneficiaría de más contexto.

        Args:
            query: La query original del usuario.
            history: Historial de conversación (opcional).

        Returns:
            RewriteResult con la query procesada.
        """
        query = query.strip()

        # ---------------------------------------------------------------------
        # Guard: Feature disabled
        # ---------------------------------------------------------------------
        if not self._enabled:
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                was_rewritten=False,
                reason="feature_disabled",
            )

        # ---------------------------------------------------------------------
        # Guard: Query ya es suficientemente clara
        # ---------------------------------------------------------------------
        if len(query) >= _MIN_QUERY_LENGTH_FOR_SKIP:
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                was_rewritten=False,
                reason="query_already_clear",
            )

        # ---------------------------------------------------------------------
        # Guard: No hay historial suficiente
        # ---------------------------------------------------------------------
        history = history or []
        if len(history) < self._min_history:
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                was_rewritten=False,
                reason="insufficient_history",
            )

        # ---------------------------------------------------------------------
        # Check: ¿La query necesita contexto?
        # ---------------------------------------------------------------------
        needs_context = self._needs_context(query)
        if not needs_context:
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                was_rewritten=False,
                reason="no_context_needed",
            )

        # ---------------------------------------------------------------------
        # Rewrite usando LLM
        # ---------------------------------------------------------------------
        try:
            rewritten = self._generate_rewrite(query, history)

            # Validar que el rewrite sea razonable
            if not rewritten or len(rewritten) > _MAX_QUERY_LENGTH:
                return RewriteResult(
                    original_query=query,
                    rewritten_query=query,
                    was_rewritten=False,
                    reason="invalid_rewrite",
                )

            # Si el LLM devolvió exactamente lo mismo, no hubo rewrite
            if rewritten.strip().lower() == query.strip().lower():
                return RewriteResult(
                    original_query=query,
                    rewritten_query=query,
                    was_rewritten=False,
                    reason="no_change_needed",
                )

            logger.info(
                "Query rewritten",
                extra={
                    "original": query[:100],
                    "rewritten": rewritten[:100],
                },
            )

            return RewriteResult(
                original_query=query,
                rewritten_query=rewritten,
                was_rewritten=True,
                reason="context_expanded",
            )

        except Exception as e:
            logger.warning(
                "Query rewrite failed, using original",
                extra={"error": str(e), "query": query[:100]},
            )
            return RewriteResult(
                original_query=query,
                rewritten_query=query,
                was_rewritten=False,
                reason=f"error: {str(e)[:50]}",
            )

    def _needs_context(self, query: str) -> bool:
        """Determina si la query se beneficiaría de contexto adicional."""
        # Queries muy cortas probablemente necesitan contexto
        if len(query) < 15:
            return True

        # Buscar patrones que indican necesidad de contexto
        for pattern in _CONTEXT_NEEDED_PATTERNS:
            if pattern.search(query):
                return True

        return False

    def _generate_rewrite(
        self,
        query: str,
        history: List[ConversationMessage],
    ) -> str:
        """Genera la query reescrita usando el LLM."""
        # Formatear historial (últimos N mensajes)
        history_text = self._format_history(history[-6:])  # Máximo 6 mensajes

        prompt = _REWRITE_PROMPT_TEMPLATE.format(
            history=history_text,
            query=query,
        )

        response = self._llm.generate_text(prompt, max_tokens=150)
        return response.strip()

    def _format_history(self, history: List[ConversationMessage]) -> str:
        """Formatea el historial para el prompt."""
        if not history:
            return "(Sin historial previo)"

        lines = []
        for msg in history:
            role = "Usuario" if msg.role == "user" else "Asistente"
            content = msg.content[:200]  # Truncar mensajes largos
            if len(msg.content) > 200:
                content += "..."
            lines.append(f"{role}: {content}")

        return "\n".join(lines)


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
def get_query_rewriter(
    llm_service: LLMRewriterPort,
    *,
    enabled: bool = True,
) -> QueryRewriter:
    """
    Factory para crear QueryRewriter.

    Args:
        llm_service: Servicio LLM con método generate_text.
        enabled: Si False, el rewriter está deshabilitado.
    """
    return QueryRewriter(llm_service, enabled=enabled)
