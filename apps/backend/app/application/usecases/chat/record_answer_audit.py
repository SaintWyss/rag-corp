# =============================================================================
# FILE: application/usecases/chat/record_answer_audit.py
# =============================================================================
"""
===============================================================================
USE CASE: Record Answer Audit (Enterprise Compliance)
===============================================================================

Name:
    Record Answer Audit Use Case

Business Goal:
    Registrar cada respuesta del RAG para compliance empresarial:
      - Trazabilidad: Quién preguntó qué, cuándo, qué fuentes se usaron
      - Auditoría: Permitir revisión posterior de respuestas
      - Métricas: Patrones de uso, áreas problemáticas
      - Legal: Documentar que el sistema advirtió sobre incertidumbre

Why (Context / Intención):
    - En empresas reguladas, cada respuesta de IA debe ser auditable.
    - Si un empleado toma una mala decisión basándose en el RAG, se puede revisar qué le dijo el sistema.
    - Permite identificar patrones: preguntas frecuentes, áreas con baja confianza, etc.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    RecordAnswerAuditUseCase

Responsibilities:
    - Crear un registro de auditoría para cada respuesta RAG.
    - Enriquecer con contexto del request (IP, user-agent, session).
    - Persistir de forma confiable (best-effort, no bloquear flujo principal).
    - Marcar respuestas de alto riesgo para revisión.

Collaborators:
    - AnswerAuditRepository: save_audit_record
===============================================================================
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Final, List, Optional, Protocol
from uuid import UUID

from ....domain.value_objects import AnswerAuditRecord

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_ANSWER_PREVIEW_MAX_LENGTH: Final[int] = 200


# -----------------------------------------------------------------------------
# Ports (Protocols)
# -----------------------------------------------------------------------------
class AuditRepositoryPort(Protocol):
    """Port for audit record persistence."""

    def save_audit_record(
        self,
        *,
        record_id: str,
        timestamp: str,
        user_id: UUID,
        workspace_id: UUID,
        query: str,
        answer_preview: str,
        confidence_level: str,
        confidence_value: float,
        requires_verification: bool,
        sources_count: int,
        source_documents: Optional[List[str]] = None,
        user_email: Optional[str] = None,
        suggested_department: Optional[str] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None: ...


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RecordAnswerAuditInput:
    """
    DTO de entrada para registrar auditoría de una respuesta.

    Campos requeridos:
      - user_id: Quién hizo la consulta
      - workspace_id: Dónde se ejecutó
      - query: Pregunta original
      - answer: Respuesta generada
      - confidence_level: "high", "medium", "low"
      - confidence_value: Score numérico [0, 1]
      - sources_count: Cantidad de fuentes usadas

    Campos opcionales:
      - requires_verification: Si se recomendó verificar
      - suggested_department: Departamento sugerido
      - source_documents: Lista de IDs de documentos fuente
      - conversation_id: ID de conversación (si aplica)
      - user_email: Email para búsqueda rápida
      - session_id: ID de sesión del browser
      - ip_address: IP del usuario
      - user_agent: User-Agent del cliente
      - response_time_ms: Tiempo de respuesta
      - metadata: Metadata adicional flexible
    """

    user_id: UUID
    workspace_id: UUID
    query: str
    answer: str
    confidence_level: str
    confidence_value: float
    sources_count: int
    requires_verification: bool = False
    suggested_department: Optional[str] = None
    source_documents: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    user_email: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    response_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordAnswerAuditResult:
    """
    DTO de salida del caso de uso.

    Campos:
      - success: True si el registro se guardó
      - record_id: ID del registro creado
      - audit_record: El registro completo (para logging/debugging)
      - error_message: Mensaje de error si falló (pero no bloquea el flujo)
    """

    success: bool = False
    record_id: Optional[str] = None
    audit_record: Optional[AnswerAuditRecord] = None
    error_message: Optional[str] = None


# -----------------------------------------------------------------------------
# Use Case
# -----------------------------------------------------------------------------
class RecordAnswerAuditUseCase:
    """
    Use Case: Registrar auditoría de una respuesta RAG.

    Estrategia:
        1) Crear AnswerAuditRecord con todos los datos.
        2) Persistir (best-effort - no bloquear el flujo principal).
        3) Loggear si es high-risk para alertas.
        4) Retornar el registro para que el caller lo use si quiere.

    Nota: Este use case es "fire-and-forget" en el sentido de que
    si falla la persistencia, solo loggea el error pero no interrumpe.
    """

    def __init__(self, audit_repository: AuditRepositoryPort) -> None:
        self._repository = audit_repository

    def execute(self, input_data: RecordAnswerAuditInput) -> RecordAnswerAuditResult:
        """
        Ejecuta el registro de auditoría.

        Este método intenta persistir pero no lanza excepciones.
        Siempre retorna un resultado (success o failure con mensaje).
        """

        # ---------------------------------------------------------------------
        # 1) Generar record_id y timestamp
        # ---------------------------------------------------------------------
        record_id = f"audit-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # ---------------------------------------------------------------------
        # 2) Crear answer preview (truncado)
        # ---------------------------------------------------------------------
        answer_preview = input_data.answer[:_ANSWER_PREVIEW_MAX_LENGTH]
        if len(input_data.answer) > _ANSWER_PREVIEW_MAX_LENGTH:
            answer_preview += "..."

        # ---------------------------------------------------------------------
        # 3) Crear el AnswerAuditRecord
        # ---------------------------------------------------------------------
        audit_record = AnswerAuditRecord(
            record_id=record_id,
            timestamp=timestamp,
            user_id=input_data.user_id,
            workspace_id=input_data.workspace_id,
            query=input_data.query,
            answer_preview=answer_preview,
            confidence_level=input_data.confidence_level,
            confidence_value=input_data.confidence_value,
            requires_verification=input_data.requires_verification,
            sources_count=input_data.sources_count,
            source_documents=input_data.source_documents,
            user_email=input_data.user_email,
            suggested_department=input_data.suggested_department,
            conversation_id=input_data.conversation_id,
            session_id=input_data.session_id,
            ip_address=input_data.ip_address,
            user_agent=input_data.user_agent,
            response_time_ms=input_data.response_time_ms,
            metadata=input_data.metadata,
        )

        # ---------------------------------------------------------------------
        # 4) Log high-risk para alertas
        # ---------------------------------------------------------------------
        if audit_record.is_high_risk:
            logger.warning(
                "HIGH RISK ANSWER GENERATED",
                extra={
                    "record_id": record_id,
                    "user_id": str(input_data.user_id),
                    "query_preview": input_data.query[:100],
                    "confidence_level": input_data.confidence_level,
                    "sources_count": input_data.sources_count,
                },
            )

        # ---------------------------------------------------------------------
        # 5) Persistir (best-effort)
        # ---------------------------------------------------------------------
        try:
            self._repository.save_audit_record(
                record_id=record_id,
                timestamp=timestamp,
                user_id=input_data.user_id,
                workspace_id=input_data.workspace_id,
                query=input_data.query,
                answer_preview=answer_preview,
                confidence_level=input_data.confidence_level,
                confidence_value=input_data.confidence_value,
                requires_verification=input_data.requires_verification,
                sources_count=input_data.sources_count,
                source_documents=input_data.source_documents,
                user_email=input_data.user_email,
                suggested_department=input_data.suggested_department,
                conversation_id=input_data.conversation_id,
                session_id=input_data.session_id,
                ip_address=input_data.ip_address,
                user_agent=input_data.user_agent,
                response_time_ms=input_data.response_time_ms,
                metadata=input_data.metadata,
            )
        except Exception as e:
            # Best-effort: log but don't fail
            logger.exception(
                "Failed to persist audit record (non-blocking)",
                extra={"record_id": record_id},
            )
            return RecordAnswerAuditResult(
                success=False,
                record_id=record_id,
                audit_record=audit_record,
                error_message=str(e),
            )

        logger.info(
            "Audit record saved",
            extra={
                "record_id": record_id,
                "confidence_level": input_data.confidence_level,
                "is_high_risk": audit_record.is_high_risk,
            },
        )

        return RecordAnswerAuditResult(
            success=True,
            record_id=record_id,
            audit_record=audit_record,
        )
