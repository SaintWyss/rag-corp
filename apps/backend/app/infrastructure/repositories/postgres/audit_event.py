"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres_audit_repo.py
============================================================
Class: PostgresAuditEventRepository

Responsibilities:
  - Persistir eventos de auditoría en PostgreSQL (tabla audit_events).
  - Listar eventos con filtros opcionales (workspace_id, actor_id, action_prefix, fechas).
  - Mantener respuestas determinísticas (orden estable) para APIs/tests.

Collaborators:
  - app.domain.audit.AuditEvent (entidad de dominio)
  - psycopg_pool.ConnectionPool (pool de conexiones)
  - psycopg.types.json.Json (JSON seguro hacia PostgreSQL)
  - crosscutting.logger.logger (observabilidad)
  - crosscutting.exceptions.DatabaseError (contrato de errores infra)

Constraints / Notes:
  - Repo puro: NO define políticas (qué auditar / autorización / RBAC).
  - Queries SIEMPRE parametrizadas (nunca interpolar input del usuario).
  - workspace_id se guarda en metadata como string: metadata->>'workspace_id' = '<uuid>'.
  - actor sigue convención del proyecto: "user:<uuid>" / "service:<hash>" / "anonymous".
============================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ....crosscutting.exceptions import DatabaseError
from ....crosscutting.logger import logger
from ....domain.audit import AuditEvent


class PostgresAuditEventRepository:
    """Repositorio PostgreSQL para auditoría (audit_events)."""

    def __init__(self, pool: ConnectionPool | None = None):
        # Pool inyectable: tests pueden pasar su pool; prod usa el pool global.
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        """Obtiene el pool: si no fue inyectado, usa la factory global."""
        if self._pool is not None:
            return self._pool

        from app.infrastructure.db.pool import get_pool

        return get_pool()

    # ------------------------------------------------------------
    # Helpers internos (DRY: errores/logging consistentes)
    # ------------------------------------------------------------
    def _fetchall(
        self,
        *,
        query: str,
        params: Iterable[object],
        error_message: str,
        extra: dict[str, object],
    ) -> list[tuple]:
        """
        Ejecuta un SELECT y devuelve todas las filas.

        Centralizamos el manejo de errores para:
        - loggear con contexto consistente
        - levantar DatabaseError con encadenamiento (from exc)
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchall()
        except Exception as exc:
            logger.exception(error_message, extra={**extra, "error": str(exc)})
            raise DatabaseError(f"{error_message}: {exc}") from exc

    # ------------------------------------------------------------
    # Escritura (append-only)
    # ------------------------------------------------------------
    def record_event(self, event: AuditEvent) -> None:
        """
        Inserta un evento de auditoría.

        Decisión:
        - Auditoría es un log append-only: no se edita, no se borra.
        - Si falla, se propaga DatabaseError; la capa superior decide si “swallow”
          (en tu proyecto, emit_audit_event ya traga errores).
        """
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_events (id, actor, action, target_id, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        event.id,
                        event.actor,
                        event.action,
                        event.target_id,
                        # metadata default defensivo: evita NULLs inesperados
                        Json(event.metadata or {}),
                    ),
                )
        except Exception as exc:
            logger.exception(
                "PostgresAuditEventRepository: Failed to record audit event",
                extra={
                    "event_id": str(getattr(event, "id", "")),
                    "actor": getattr(event, "actor", None),
                    "action": getattr(event, "action", None),
                    "error": str(exc),
                },
            )
            raise DatabaseError(f"Failed to record audit event: {exc}") from exc

    # ------------------------------------------------------------
    # Lectura (listado con filtros)
    # ------------------------------------------------------------
    def list_events(
        self,
        *,
        workspace_id: UUID | None = None,
        actor_id: str | None = None,
        action_prefix: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """
        Lista eventos con filtros opcionales.

        Filtros soportados:
        - workspace_id:
            Se guarda en JSONB metadata como string:
            metadata["workspace_id"] = "<uuid>"
            => filtramos con metadata->>'workspace_id' = %s

        - actor_id:
            En el proyecto actor se normaliza como:
              "user:<uuid>" o "service:<hash>" o "anonymous"
            Por eso:
              * si actor_id ya trae ":", es un match exacto (actor = %s)
              * si NO trae ":", asumimos que es un id “crudo” (uuid/hash) y
                buscamos por sufijo ":%actor_id" (actor LIKE %s)

        - action_prefix:
            Match prefix por LIKE: "workspaces." -> "workspaces.%"

        - start_at / end_at:
            Rango inclusivo (>=, <=) por simplicidad y compatibilidad.

        Orden:
        - created_at DESC, id DESC -> estable incluso con timestamps iguales.
        """
        # Guard rails: evita queries raras y hace el método “totalmente predecible”.
        if limit <= 0:
            return []
        if offset < 0:
            offset = 0

        conditions: list[str] = []
        params: list[object] = []

        # ---- workspace_id (scope por workspace vía metadata JSONB)
        if workspace_id is not None:
            conditions.append("metadata->>'workspace_id' = %s")
            params.append(str(workspace_id))

        # ---- actor_id (match exacto o por sufijo)
        if actor_id:
            if ":" in actor_id:
                # Ej: "user:<uuid>" o "service:<hash>"
                conditions.append("actor = %s")
                params.append(actor_id)
            else:
                # Ej: "<uuid>" -> matchea "user:<uuid>" o "service:<uuid-like>"
                conditions.append("actor LIKE %s")
                params.append(f"%:{actor_id}")

        # ---- action prefix
        if action_prefix:
            conditions.append("action LIKE %s")
            params.append(f"{action_prefix}%")

        # ---- rango temporal
        if start_at is not None:
            conditions.append("created_at >= %s")
            params.append(start_at)

        if end_at is not None:
            conditions.append("created_at <= %s")
            params.append(end_at)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, actor, action, target_id, metadata, created_at
            FROM audit_events
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
        """

        rows = self._fetchall(
            query=query,
            params=[*params, limit, offset],
            error_message="PostgresAuditEventRepository: Failed to list audit events",
            extra={
                "workspace_id": str(workspace_id) if workspace_id else None,
                "actor_id": actor_id,
                "action_prefix": action_prefix,
                "start_at": start_at.isoformat() if start_at else None,
                "end_at": end_at.isoformat() if end_at else None,
                "limit": limit,
                "offset": offset,
            },
        )

        # Mapping explícito: fácil de mantener / debuggear.
        events: list[AuditEvent] = []
        for event_id, actor, action, target_id, metadata, created_at in rows:
            events.append(
                AuditEvent(
                    id=event_id,
                    actor=actor,
                    action=action,
                    target_id=target_id,
                    metadata=metadata or {},
                    created_at=created_at,
                )
            )

        return events
