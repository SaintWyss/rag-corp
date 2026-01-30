"""
============================================================
TARJETA CRC — infrastructure/repositories/postgres_audit_repo.py
============================================================
Class: PostgresAuditEventRepository

Responsibilities:
- Persistir eventos de auditoría en PostgreSQL (tabla audit_events).
- Proveer listados filtrables (actor, action_prefix, rango de fechas).
- Permitir “scoping” por workspace vía metadata->>'workspace_id' (cuando aplique).

Collaborators:
- domain.audit.AuditEvent (entidad de dominio)
- psycopg_pool.ConnectionPool (pool de conexiones)
- psycopg.types.json.Json (serialización segura JSON)
- crosscutting.logger.logger
- crosscutting.exceptions.DatabaseError

Constraints / Notes (Clean / KISS):
- Repo puro: NO decide políticas de auditoría (qué se audita / cuándo).
- Queries SIEMPRE parametrizadas.
- Ordenamiento determinístico: created_at DESC, id DESC (desempate estable).
- workspace_id se filtra por JSONB metadata: conviene índice por performance (ver mejoras).
============================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID

from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from ...crosscutting.exceptions import DatabaseError
from ...crosscutting.logger import logger
from ...domain.audit import AuditEvent


class PostgresAuditEventRepository:
    """
    Repositorio PostgreSQL para auditoría.

    Modelo mental:
    - audit_events es un log append-only.
    - metadata (JSONB) permite “payload” flexible y filtros por claves (ej workspace_id).
    """

    def __init__(self, pool: ConnectionPool | None = None):
        # Pool inyectable para tests / ambientes controlados.
        self._pool = pool

    def _get_pool(self) -> ConnectionPool:
        """Lazy-load del pool global si no fue inyectado."""
        if self._pool is not None:
            return self._pool

        from ..db.pool import get_pool

        return get_pool()

    # ============================================================
    # Helpers DB (DRY: errores y logging consistentes)
    # ============================================================
    def _fetchall(
        self,
        *,
        query: str,
        params: Iterable[object],
        context_msg: str,
        extra: dict,
    ) -> list[tuple]:
        """Ejecuta un SELECT y devuelve todas las filas."""
        try:
            pool = self._get_pool()
            with pool.connection() as conn:
                return conn.execute(query, tuple(params)).fetchall()
        except Exception as exc:
            logger.exception(context_msg, extra={**extra, "error": str(exc)})
            raise DatabaseError(f"{context_msg}: {exc}") from exc

    # ============================================================
    # Escritura (append-only)
    # ============================================================
    def record_event(self, event: AuditEvent) -> None:
        """
        Inserta un evento de auditoría.

        Diseño:
        - Append-only: no hay UPDATE/DELETE en auditoría.
        - metadata se persiste como JSONB.
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
                        Json(event.metadata or {}),
                    ),
                )
        except Exception as exc:
            logger.exception(
                "PostgresAuditEventRepository: Failed to record audit event",
                extra={
                    "error": str(exc),
                    "event_id": str(getattr(event, "id", "")),
                    "actor": getattr(event, "actor", None),
                    "action": getattr(event, "action", None),
                },
            )
            raise DatabaseError(f"Failed to record audit event: {exc}") from exc

    # ============================================================
    # Lectura (listado con filtros)
    # ============================================================
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

        Filtros:
        - workspace_id: metadata->>'workspace_id' = '<uuid>'
          (esto asume que vos guardás esa key como string en metadata)
        - actor_id:
            * si viene con ":", se asume "tipo:uuid" exacto
            * si viene sin ":", se busca por sufijo ":%actor_id" (compat con tu formato)
        - action_prefix: "LOGIN_" -> "LOGIN_%"
        - start_at/end_at: rango temporal inclusivo

        Orden:
        - created_at DESC, id DESC para estabilidad cuando hay mismos timestamps.
        """
        # Guard rails: evita queries raras / inputs negativos
        if limit <= 0:
            return []
        if offset < 0:
            offset = 0

        conditions: list[str] = []
        params: list[object] = []

        # ---- workspace_id (JSONB) ----
        if workspace_id:
            # metadata almacena strings: comparamos con string uuid.
            conditions.append("metadata->>'workspace_id' = %s")
            params.append(str(workspace_id))

        # ---- actor_id ----
        if actor_id:
            # Convención: actor = "<kind>:<id>" (ej: "user:2f..." o "api_key:abc")
            if ":" in actor_id:
                conditions.append("actor = %s")
                params.append(actor_id)
            else:
                # Busca por sufijo ":%actor_id" para matchear kind variable.
                # Ej: actor_id="2f..." -> "user:2f..."
                conditions.append("actor LIKE %s")
                params.append(f"%:{actor_id}")

        # ---- action_prefix ----
        if action_prefix:
            conditions.append("action LIKE %s")
            params.append(f"{action_prefix}%")

        # ---- fecha inicio/fin ----
        if start_at:
            conditions.append("created_at >= %s")
            params.append(start_at)

        if end_at:
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
            context_msg="PostgresAuditEventRepository: Failed to list audit events",
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

        # Mapping explícito (fácil de leer/maintain).
        events: list[AuditEvent] = []
        for row in rows:
            event_id, actor, action, target_id, metadata, created_at = row
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
