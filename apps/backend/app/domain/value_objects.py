# =============================================================================
# FILE: domain/value_objects.py
# =============================================================================
"""
===============================================================================
TARJETA CRC — domain/value_objects.py
===============================================================================

Módulo:
    Objetos de Valor del Dominio (inmutables)

Responsabilidades:
    - Representar conceptos sin identidad propia (igualdad por valor).
    - Validar invariantes en constructor (__post_init__).
    - Facilitar serialización (to_dict) para capa de interfaces.

Objetos incluidos:
    - SourceReference
    - ConfidenceScore + calculate_confidence
    - MetadataFilter
    - UsageQuota
    - FeedbackVote
    - AnswerAuditRecord

Colaboradores:
    - domain.entities.QueryResult: puede incluir sources/confidence.
    - repositorios/auditoría: persisten AnswerAuditRecord.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Final, List, Optional
from uuid import UUID

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
_MIN_CONFIDENCE: Final[float] = 0.0
_MAX_CONFIDENCE: Final[float] = 1.0


# -----------------------------------------------------------------------------
# SourceReference (cita estructurada)
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SourceReference:
    """
    Referencia estructurada a una fuente usada en una respuesta.

    Permite a UI mostrar fuentes sin parsear texto.
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
# ConfidenceScore
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """Score de confianza normalizado [0,1] + metadata para UI y auditoría."""

    value: float
    user_message: str = ""
    internal_reasoning: Optional[str] = None
    factors: Dict[str, float] = field(default_factory=dict)
    requires_verification: bool = False
    suggested_department: Optional[str] = None

    def __post_init__(self) -> None:
        if not (_MIN_CONFIDENCE <= self.value <= _MAX_CONFIDENCE):
            raise ValueError(f"ConfidenceScore fuera de rango: {self.value}")

    @property
    def level(self) -> str:
        if self.value >= 0.8:
            return "high"
        if self.value >= 0.5:
            return "medium"
        return "low"

    @property
    def display_message(self) -> str:
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
    """Calcula un ConfidenceScore basado en factores observables."""
    factors: Dict[str, float] = {}

    # 1) Cobertura de evidencia (chunks)
    if chunks_available > 0:
        chunk_factor = min(1.0, chunks_used / max(3, chunks_available * 0.5))
    else:
        chunk_factor = 0.0
    factors["chunk_coverage"] = round(chunk_factor, 2)

    # 2) Longitud como proxy de completitud
    if response_length < 50:
        length_factor = 0.3
    elif response_length < 200:
        length_factor = 0.7
    else:
        length_factor = 1.0
    factors["response_completeness"] = round(length_factor, 2)

    # 3) Match exacto
    match_factor = 1.0 if has_exact_match else 0.7
    factors["keyword_match"] = round(match_factor, 2)

    # 4) Frescura de fuentes (si hay dato)
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
        freshness_factor = 0.8

    # Score final ponderado
    score = (
        chunk_factor * 0.35
        + length_factor * 0.25
        + match_factor * 0.20
        + freshness_factor * 0.20
    )

    requires_verification = score < 0.7 or chunks_used < 2

    department_map = {
        "legal": "Legales",
        "finance": "Finanzas",
        "hr": "Recursos Humanos",
        "it": "Sistemas",
        "compliance": "Compliance",
        "operations": "Operaciones",
    }
    suggested_dept = department_map.get(topic_category or "")

    reasoning_parts: list[str] = []
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
# MetadataFilter
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class MetadataFilter:
    """Filtro de metadatos para retrieval."""

    field: str
    operator: str  # "eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"
    value: Any

    def __post_init__(self) -> None:
        valid = {"eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"}
        if self.operator not in valid:
            raise ValueError(f"Operador inválido '{self.operator}'. Válidos: {valid}")

    def to_dict(self) -> Dict[str, Any]:
        return {"field": self.field, "operator": self.operator, "value": self.value}


# -----------------------------------------------------------------------------
# UsageQuota
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class UsageQuota:
    """Cuota de uso para rate limiting."""

    limit: int
    used: int
    reset_at: Optional[str] = None
    resource: str = "messages"

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def is_exceeded(self) -> bool:
        return self.used >= self.limit

    @property
    def usage_percentage(self) -> float:
        if self.limit <= 0:
            return 100.0
        return min(100.0, (self.used / self.limit) * 100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "reset_at": self.reset_at,
            "resource": self.resource,
            "is_exceeded": self.is_exceeded,
        }


# -----------------------------------------------------------------------------
# FeedbackVote
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FeedbackVote:
    """Voto de feedback sobre una respuesta."""

    vote: str  # "up", "down", "neutral"
    comment: Optional[str] = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        valid = {"up", "down", "neutral"}
        if self.vote not in valid:
            raise ValueError(f"Voto inválido '{self.vote}'. Válidos: {valid}")

    @property
    def is_positive(self) -> bool:
        return self.vote == "up"

    @property
    def is_negative(self) -> bool:
        return self.vote == "down"

    def to_dict(self) -> Dict[str, Any]:
        return {"vote": self.vote, "comment": self.comment, "tags": list(self.tags)}


# -----------------------------------------------------------------------------
# AnswerAuditRecord
# -----------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AnswerAuditRecord:
    """Registro de auditoría de respuestas para trazabilidad/cumplimiento."""

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
        return self.confidence_level == "low" or self.sources_count < 2

    @property
    def audit_summary(self) -> str:
        risk = " [ALTO RIESGO]" if self.is_high_risk else ""
        return (
            f"[{self.timestamp}] User={self.user_email or self.user_id} "
            f"Query='{self.query[:50]}...' Confidence={self.confidence_level} "
            f"Sources={self.sources_count}{risk}"
        )

    def to_dict(self) -> Dict[str, Any]:
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
