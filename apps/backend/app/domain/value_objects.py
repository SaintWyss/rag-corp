# =============================================================================
# FILE: domain/value_objects.py
# =============================================================================
"""
===============================================================================
DOMAIN: Value Objects (Immutable Domain Primitives)
===============================================================================

Name:
    Domain Value Objects

Qué es:
    Objetos de valor inmutables que representan conceptos del dominio
    sin identidad propia. Son iguales si sus atributos son iguales.

Contenido:
    - SourceReference: Referencia estructurada a una fuente/chunk
    - ConfidenceScore: Score de confianza de una respuesta
    - MetadataFilter: Filtro de metadatos para retrieval
    - UsageQuota: Cuota de uso para rate limiting

Principios:
    - Inmutabilidad (frozen dataclasses)
    - Validación en constructor
    - Sin side effects
    - Equality por valor

===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Final, List, Optional
from uuid import UUID

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_MIN_CONFIDENCE: Final[float] = 0.0
_MAX_CONFIDENCE: Final[float] = 1.0


# -----------------------------------------------------------------------------
# Source Reference (Structured Citation)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SourceReference:
    """
    Referencia estructurada a una fuente usada en una respuesta RAG.

    Permite al frontend renderizar "chips" o tarjetas clickeables con la info
    de cada fuente, sin tener que parsear texto.

    Attributes:
        index: Índice de la fuente en la respuesta ([S1], [S2], etc.)
        document_id: ID del documento original
        document_title: Título del documento (si existe)
        chunk_id: ID del chunk específico
        chunk_index: Índice del chunk dentro del documento (0-based)
        page_number: Número de página (si aplica, ej: PDFs)
        source_url: URL o path del documento original
        relevance_score: Score de similitud/relevancia (0-1)
        snippet: Extracto corto del contenido (para preview)
    """

    index: int
    document_id: Optional[UUID] = None
    document_title: Optional[str] = None
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    source_url: Optional[str] = None
    relevance_score: Optional[float] = None
    snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario para JSON responses."""
        return {
            "index": self.index,
            "document_id": str(self.document_id) if self.document_id else None,
            "document_title": self.document_title,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "source_url": self.source_url,
            "relevance_score": self.relevance_score,
            "snippet": self.snippet,
        }


# -----------------------------------------------------------------------------
# Confidence Score (Answer Quality Indicator - Enterprise Focus)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """
    Score de confianza para una respuesta RAG - Enfoque Empresarial.

    Propósito:
        - Indicar al usuario si debe verificar la respuesta con un experto.
        - Documentar para compliance que el sistema advirtió sobre incertidumbre.
        - Permitir métricas de calidad del knowledge base.

    Niveles (para UI):
        - "high" (≥0.8): "Respuesta basada en múltiples fuentes verificadas."
        - "medium" (0.5-0.79): "Respuesta parcial. Verificar con el área correspondiente."
        - "low" (<0.5): "Información limitada. Consultar directamente con un especialista."

    Attributes:
        value: Score normalizado [0, 1]
        level: Nivel categórico ("high", "medium", "low")
        user_message: Mensaje legible para mostrar al usuario
        internal_reasoning: Explicación técnica (para logs/debugging)
        factors: Factores que contribuyeron al score
        requires_verification: True si se recomienda verificación humana
        suggested_department: Departamento sugerido para verificar (si aplica)
    """

    value: float
    user_message: str = ""
    internal_reasoning: Optional[str] = None
    factors: Dict[str, float] = field(default_factory=dict)
    requires_verification: bool = False
    suggested_department: Optional[str] = None

    def __post_init__(self) -> None:
        """Valida que el score esté en rango válido."""
        if not (_MIN_CONFIDENCE <= self.value <= _MAX_CONFIDENCE):
            raise ValueError(
                f"Confidence score must be between {_MIN_CONFIDENCE} and {_MAX_CONFIDENCE}, "
                f"got {self.value}"
            )

    @property
    def level(self) -> str:
        """Nivel categórico del score para UI."""
        if self.value >= 0.8:
            return "high"
        if self.value >= 0.5:
            return "medium"
        return "low"

    @property
    def display_message(self) -> str:
        """Mensaje para mostrar al usuario basado en el nivel."""
        if self.user_message:
            return self.user_message

        if self.level == "high":
            return "Respuesta basada en múltiples fuentes verificadas."
        if self.level == "medium":
            dept = (
                f" con {self.suggested_department}" if self.suggested_department else ""
            )
            return f"Respuesta parcial. Se recomienda verificar{dept}."
        return "Información limitada. Consultar directamente con un especialista."

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario para JSON responses."""
        return {
            "value": round(self.value, 2),
            "level": self.level,
            "display_message": self.display_message,
            "requires_verification": self.requires_verification,
            "suggested_department": self.suggested_department,
            "factors": self.factors,
        }


def calculate_confidence(
    *,
    chunks_used: int,
    chunks_available: int,
    response_length: int,
    has_exact_match: bool = False,
    source_recency_days: Optional[int] = None,
    topic_category: Optional[str] = None,
) -> ConfidenceScore:
    """
    Calcula un ConfidenceScore basado en factores objetivos.

    Factores considerados:
        - chunk_coverage: Proporción de chunks usados vs disponibles
        - response_completeness: Si la respuesta tiene longitud adecuada
        - source_freshness: Antigüedad de las fuentes (si aplica)
        - exact_match_bonus: Bonus si hubo match exacto de keywords

    Args:
        chunks_used: Cantidad de chunks incluidos en el contexto
        chunks_available: Cantidad total de chunks recuperados
        response_length: Longitud de la respuesta en caracteres
        has_exact_match: True si algún chunk tiene match exacto con el query
        source_recency_days: Días desde la última actualización de las fuentes
        topic_category: Categoría del tema (para sugerir departamento)

    Returns:
        ConfidenceScore con todos los factores calculados.
    """
    factors: Dict[str, float] = {}

    # Factor 1: Cobertura de chunks (más chunks = más evidencia)
    if chunks_available > 0:
        chunk_factor = min(1.0, chunks_used / max(3, chunks_available * 0.5))
    else:
        chunk_factor = 0.0
    factors["chunk_coverage"] = round(chunk_factor, 2)

    # Factor 2: Completitud de respuesta
    if response_length < 50:
        length_factor = 0.3  # Muy corta, posiblemente evasiva
    elif response_length < 200:
        length_factor = 0.7  # Aceptable
    else:
        length_factor = 1.0  # Completa
    factors["response_completeness"] = round(length_factor, 2)

    # Factor 3: Match exacto (bonus si el query matchea directamente)
    match_factor = 1.0 if has_exact_match else 0.7
    factors["keyword_match"] = round(match_factor, 2)

    # Factor 4: Frescura de fuentes (opcional)
    if source_recency_days is not None:
        if source_recency_days <= 30:
            freshness_factor = 1.0
        elif source_recency_days <= 180:
            freshness_factor = 0.8
        elif source_recency_days <= 365:
            freshness_factor = 0.6
        else:
            freshness_factor = 0.4
        factors["source_freshness"] = round(freshness_factor, 2)
    else:
        freshness_factor = 0.8  # Neutral si no hay data

    # Score final (promedio ponderado)
    score = (
        chunk_factor * 0.35
        + length_factor * 0.25
        + match_factor * 0.20
        + freshness_factor * 0.20
    )

    # Determinar si requiere verificación
    requires_verification = score < 0.7 or chunks_used < 2

    # Mapear categoría a departamento
    department_map = {
        "legal": "Legales",
        "finance": "Finanzas",
        "hr": "Recursos Humanos",
        "it": "Sistemas",
        "compliance": "Compliance",
        "operations": "Operaciones",
    }
    suggested_dept = department_map.get(topic_category or "")

    # Generar razón interna (para logs)
    reasoning_parts = []
    if chunk_factor < 0.5:
        reasoning_parts.append("pocas fuentes disponibles")
    if length_factor < 0.7:
        reasoning_parts.append("respuesta breve")
    if freshness_factor < 0.6:
        reasoning_parts.append("fuentes desactualizadas")

    internal_reasoning = (
        "Factores: " + ", ".join(reasoning_parts)
        if reasoning_parts
        else "Todos los factores en rango normal"
    )

    return ConfidenceScore(
        value=round(score, 2),
        internal_reasoning=internal_reasoning,
        factors=factors,
        requires_verification=requires_verification,
        suggested_department=suggested_dept,
    )


# -----------------------------------------------------------------------------
# Metadata Filter (Retrieval Filtering)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class MetadataFilter:
    """
    Filtro de metadatos para retrieval.

    Permite filtrar chunks por atributos como departamento, año, tipo de doc, etc.

    Attributes:
        field: Nombre del campo de metadata a filtrar
        operator: Operador de comparación
        value: Valor a comparar
    """

    field: str
    operator: str  # "eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"
    value: Any

    def __post_init__(self) -> None:
        """Valida el operador."""
        valid_operators = {"eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"}
        if self.operator not in valid_operators:
            raise ValueError(
                f"Invalid operator '{self.operator}'. Valid: {valid_operators}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }


# -----------------------------------------------------------------------------
# Usage Quota (Rate Limiting)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class UsageQuota:
    """
    Cuota de uso para rate limiting.

    Representa el estado de consumo de un recurso (mensajes, tokens, etc.)
    para un scope determinado (usuario, workspace, etc.).

    Attributes:
        limit: Límite máximo del período
        used: Cantidad consumida en el período actual
        remaining: Cantidad restante (calculada)
        reset_at: Timestamp de reset del período (ISO 8601)
        resource: Nombre del recurso ("messages", "tokens", etc.)
    """

    limit: int
    used: int
    reset_at: Optional[str] = None
    resource: str = "messages"

    @property
    def remaining(self) -> int:
        """Cantidad restante disponible."""
        return max(0, self.limit - self.used)

    @property
    def is_exceeded(self) -> bool:
        """True si se excedió la cuota."""
        return self.used >= self.limit

    @property
    def usage_percentage(self) -> float:
        """Porcentaje de uso (0-100)."""
        if self.limit <= 0:
            return 100.0
        return min(100.0, (self.used / self.limit) * 100)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario para headers/responses."""
        return {
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "reset_at": self.reset_at,
            "resource": self.resource,
            "is_exceeded": self.is_exceeded,
        }


# -----------------------------------------------------------------------------
# Feedback Vote (RLHF)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FeedbackVote:
    """
    Voto de feedback del usuario sobre una respuesta.

    Attributes:
        vote: Tipo de voto ("up", "down", "neutral")
        comment: Comentario opcional del usuario
        tags: Tags de categorización (ej: ["incorrect", "incomplete"])
    """

    vote: str  # "up", "down", "neutral"
    comment: Optional[str] = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Valida el tipo de voto."""
        valid_votes = {"up", "down", "neutral"}
        if self.vote not in valid_votes:
            raise ValueError(f"Invalid vote '{self.vote}'. Valid: {valid_votes}")

    @property
    def is_positive(self) -> bool:
        """True si es voto positivo."""
        return self.vote == "up"

    @property
    def is_negative(self) -> bool:
        """True si es voto negativo."""
        return self.vote == "down"

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "vote": self.vote,
            "comment": self.comment,
            "tags": list(self.tags),
        }


# -----------------------------------------------------------------------------
# Answer Audit Record (Enterprise Compliance / Traceability)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AnswerAuditRecord:
    """
    Registro de auditoría para cada respuesta generada por el RAG.

    Propósito Empresarial:
        - Trazabilidad: Quién preguntó qué, cuándo, y qué fuentes se usaron.
        - Compliance: Documentar que el sistema advirtió sobre incertidumbre.
        - Investigación: Si un usuario tomó una mala decisión, poder revisar qué le dijo el sistema.
        - Métricas: Analizar patrones de uso, preguntas frecuentes, áreas problemáticas.

    Retención:
        - Este registro debe persistirse para auditoría.
        - Política de retención típica: 1-7 años según regulación.

    Attributes:
        record_id: ID único del registro
        timestamp: Momento de la consulta (ISO 8601 UTC)
        user_id: ID del usuario que hizo la consulta
        user_email: Email del usuario (para búsqueda rápida)
        workspace_id: Workspace donde se ejecutó la consulta
        query: Pregunta original del usuario
        answer_preview: Primeros N caracteres de la respuesta (para búsqueda)
        confidence_level: Nivel de confianza ("high", "medium", "low")
        confidence_value: Score numérico de confianza
        requires_verification: Si el sistema recomendó verificar
        suggested_department: Departamento sugerido para verificación
        sources_count: Cantidad de fuentes usadas
        source_documents: Lista de IDs de documentos fuente
        conversation_id: ID de la conversación (si aplica)
        session_id: ID de sesión del usuario
        ip_address: IP del usuario (para seguridad)
        user_agent: User-Agent del cliente
        response_time_ms: Tiempo de respuesta en milisegundos
        was_rated: Si el usuario dio feedback
        rating: Rating del usuario (si dio feedback)
        metadata: Metadata adicional flexible
    """

    record_id: str
    timestamp: str
    user_id: UUID
    workspace_id: UUID
    query: str
    answer_preview: str
    confidence_level: str
    confidence_value: float
    requires_verification: bool
    sources_count: int
    source_documents: List[str] = field(default_factory=list)
    user_email: Optional[str] = None
    suggested_department: Optional[str] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    response_time_ms: Optional[int] = None
    was_rated: bool = False
    rating: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_risk(self) -> bool:
        """
        Indica si esta consulta es de alto riesgo para auditoría.

        Alto riesgo si:
          - Confianza baja
          - Requiere verificación
          - Pocas fuentes
        """
        return self.confidence_level == "low" or self.sources_count < 2

    @property
    def audit_summary(self) -> str:
        """Resumen legible para logs de auditoría."""
        risk_flag = " [ALTO RIESGO]" if self.is_high_risk else ""
        return (
            f"[{self.timestamp}] User={self.user_email or self.user_id} "
            f"Query='{self.query[:50]}...' Confidence={self.confidence_level} "
            f"Sources={self.sources_count}{risk_flag}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario para persistencia."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "user_id": str(self.user_id),
            "user_email": self.user_email,
            "workspace_id": str(self.workspace_id),
            "query": self.query,
            "answer_preview": self.answer_preview,
            "confidence_level": self.confidence_level,
            "confidence_value": self.confidence_value,
            "requires_verification": self.requires_verification,
            "suggested_department": self.suggested_department,
            "sources_count": self.sources_count,
            "source_documents": self.source_documents,
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "response_time_ms": self.response_time_ms,
            "was_rated": self.was_rated,
            "rating": self.rating,
            "is_high_risk": self.is_high_risk,
            "metadata": self.metadata,
        }
