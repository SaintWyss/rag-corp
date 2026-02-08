"""
============================================================
TARJETA CRC — infrastructure/repositories/in_memory_workspace_acl_repo.py
============================================================
Class: InMemoryWorkspaceAclRepository

Responsibilities:
  - Almacenar ACLs de workspaces en memoria (tests / local dev).
  - Exponer operaciones mínimas tipo CRUD para listas de acceso (workspace_acl).
  - Soportar reverse lookup: dado un user_id, devolver workspaces donde está compartido.
  - Mantener ordering determinístico para tests estables.

Collaborators:
  - domain.repositories.WorkspaceAclRepository (contrato)
  - uuid.UUID (identificadores)

Constraints / Notes (Clean / SOLID):
  - Thread-safe: Lock protege el diccionario interno.
  - Repo puro: NO decide RBAC, sólo persiste/retorna datos.
  - Copias defensivas: evita aliasing de listas mutables.
  - Dedupe: no se permiten duplicados (replica el PK compuesto del Postgres).
  - Orden determinístico:
      - list_workspace_acl: por insertion order (estable desde Python 3.7+)
      - list_workspaces_for_user: orden lexicográfico por UUID (string) para tests
============================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Iterable, List
from uuid import UUID

from ....domain.entities import AclEntry, AclRole
from ....domain.repositories import WorkspaceAclRepository


class InMemoryWorkspaceAclRepository(WorkspaceAclRepository):
    """
    Repositorio in-memory, thread-safe, para ACL de workspaces.

    Modelo mental:
    - _acls actúa como tabla:
        workspace_id -> [user_id, user_id, ...]
    - Mantiene una lista sin duplicados por workspace.
    - Reverse lookup recorre la tabla (O(n)), aceptable para tests/local.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._acls: Dict[UUID, List[UUID]] = {}
        # Almacén enriquecido para ACL management (grant/revoke/list_entries)
        self._entries: Dict[UUID, Dict[UUID, AclEntry]] = {}

    # =========================================================
    # Helpers internos
    # =========================================================
    @staticmethod
    def _dedupe_preserve_order(user_ids: Iterable[UUID]) -> List[UUID]:
        """
        Deduplica preservando orden de llegada.

        Por qué:
        - Replica el PK compuesto (workspace_id, user_id) de Postgres:
          no debería haber duplicados.
        - Preservar orden hace que sea más fácil debuggear tests (y estable).
        """
        seen: set[UUID] = set()
        unique: List[UUID] = []
        for uid in user_ids:
            if uid in seen:
                continue
            seen.add(uid)
            unique.append(uid)
        return unique

    # =========================================================
    # API del repositorio
    # =========================================================
    def list_workspace_acl(self, workspace_id: UUID) -> List[UUID]:
        """
        Devuelve user_ids que tienen acceso al workspace.

        Decisión:
        - Retornamos una COPIA para que el caller no mutile el estado interno.
        - Orden: el orden de inserción (estable).
        """
        with self._lock:
            return list(self._acls.get(workspace_id, []))

    def list_workspaces_for_user(self, user_id: UUID) -> List[UUID]:
        """
        Reverse lookup: devuelve workspace_ids donde user_id está presente.

        Orden determinístico:
        - Ordenamos por str(UUID) para estabilidad total en tests y snapshots.
        """
        with self._lock:
            workspace_ids = [
                ws_id for ws_id, users in self._acls.items() if user_id in users
            ]

        # Orden estable y determinístico (independiente del insertion order del dict).
        workspace_ids.sort(key=lambda ws_id: str(ws_id))
        return workspace_ids

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: List[UUID]) -> None:
        """
        Reemplaza la ACL completa del workspace por la lista provista.

        Semántica:
        - "Replace" significa:
            1) borrar estado anterior
            2) persistir el nuevo set
        - Dedupe + copia defensiva para evitar:
            - duplicados
            - aliasing (caller modifica la lista original)
        """
        unique_ids = self._dedupe_preserve_order(user_ids)
        with self._lock:
            self._acls[workspace_id] = unique_ids
            # Sincronizar _entries: recrear con VIEWER default
            self._entries[workspace_id] = {
                uid: AclEntry(
                    workspace_id=workspace_id,
                    user_id=uid,
                    role=AclRole.VIEWER,
                    created_at=datetime.now(timezone.utc),
                )
                for uid in unique_ids
            }

    # =========================================================
    # ACL Management (grant / revoke / list_entries)
    # =========================================================
    def grant_access(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: AclRole = AclRole.VIEWER,
        *,
        granted_by: UUID | None = None,
    ) -> AclEntry:
        """Otorga acceso (upsert). Retorna la entrada creada/actualizada."""
        with self._lock:
            ws_entries = self._entries.setdefault(workspace_id, {})
            ws_acl = self._acls.setdefault(workspace_id, [])

            entry = AclEntry(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                granted_by=granted_by,
                created_at=datetime.now(timezone.utc),
            )
            ws_entries[user_id] = entry

            # Mantener _acls sincronizado
            if user_id not in ws_acl:
                ws_acl.append(user_id)

            return entry

    def revoke_access(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Revoca acceso. Retorna True si existía."""
        with self._lock:
            ws_entries = self._entries.get(workspace_id, {})
            existed = user_id in ws_entries
            ws_entries.pop(user_id, None)

            # Mantener _acls sincronizado
            ws_acl = self._acls.get(workspace_id, [])
            if user_id in ws_acl:
                ws_acl.remove(user_id)

            return existed

    def list_acl_entries(self, workspace_id: UUID) -> list[AclEntry]:
        """Lista entradas ACL con rol y metadata."""
        with self._lock:
            ws_entries = self._entries.get(workspace_id, {})
            # Orden determinístico por insertion order (consistente con _acls)
            return list(ws_entries.values())
