"""
============================================================
TARJETA CRC — infrastructure/repositories/in_memory_workspace_repo.py
============================================================
Class: InMemoryWorkspaceRepository

Responsibilities:
  - Almacenar workspaces en memoria (tests / local dev / fallback simple).
  - Implementar CRUD mínimo + semántica de archivado (archived_at).
  - Proveer helpers de listado usados por casos de uso:
      - list_workspaces_by_visibility
      - list_workspaces_by_ids
      - list_workspaces_visible_to_user (por contrato del use case)
  - Mantener ordering determinístico alineado con Postgres:
      ORDER BY created_at DESC NULLS LAST, name ASC

Collaborators:
  - domain.entities.Workspace, WorkspaceVisibility (entidades/enum del dominio)
  - domain.repositories.WorkspaceRepository (contrato a implementar)

Constraints / Notes (Clean Code / Maintainability):
  - Thread-safe: acceso protegido por Lock.
  - Repo puro: NO aplica RBAC “real” ni decisiones de negocio complejas.
    (Sólo replica el comportamiento esperado por los use cases para tests).
  - Copias defensivas: evita compartir listas mutables entre callers.
============================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from ....domain.entities import Workspace, WorkspaceVisibility
from ....domain.repositories import WorkspaceRepository


class InMemoryWorkspaceRepository(WorkspaceRepository):
    """
    Repositorio in-memory, thread-safe, para Workspaces.

    Modelo mental:
    - _workspaces es la "tabla" en memoria (UUID -> Workspace).
    - Cada operación lee/escribe bajo lock para evitar condiciones de carrera.
    - Se devuelve ordering determinístico para que los tests sean estables.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._workspaces: Dict[UUID, Workspace] = {}

    # =========================================================
    # Helpers internos (DRY, legibilidad, invariantes)
    # =========================================================
    @staticmethod
    def _now() -> datetime:
        """R: Fuente única de tiempo (UTC) para consistencia en tests."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _created_sort_key(w: Workspace) -> datetime:
        """
        R: Emula 'NULLS LAST' para created_at cuando ordenamos DESC.

        - Si created_at es None, lo tratamos como "muy viejo" para que quede al final.
        - Importante: usamos UTC para mantener coherencia.
        """
        return w.created_at or datetime.min.replace(tzinfo=timezone.utc)

    @classmethod
    def _sorted(cls, items: Iterable[Workspace]) -> List[Workspace]:
        """
        R: Devuelve una lista nueva ordenada (no muta input).

        Orden alineado con Postgres repo:
          ORDER BY created_at DESC NULLS LAST, name ASC

        Nota: usar 'sorted' (no sort in-place) reduce efectos colaterales y
        hace más fácil razonar/maintain.
        """
        return sorted(
            list(items),
            key=lambda w: (
                -cls._created_sort_key(w).timestamp(),  # DESC (más nuevo primero)
                (w.name or ""),  # ASC por nombre (fallback defensivo)
            ),
        )

    @staticmethod
    def _is_archived(w: Workspace) -> bool:
        """R: Semántica única de archivado (soft delete)."""
        return w.archived_at is not None

    @staticmethod
    def _normalize_name(name: str) -> str:
        """R: Normalización consistente para checks de unicidad."""
        return name.strip().lower()

    @staticmethod
    def _copy_roles(roles: list[str] | None) -> list[str]:
        """R: Copia defensiva para evitar aliasing de listas mutables."""
        return list(roles or [])

    @staticmethod
    def _copy_shared_ids(ids: list[UUID] | None) -> list[UUID]:
        """R: Copia defensiva de shared_user_ids."""
        return list(ids or [])

    # =========================================================
    # Listados
    # =========================================================
    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        Lista workspaces, opcionalmente filtrando por owner.

        - include_archived=False => excluye archived_at != NULL
        - ordering determinístico alineado a Postgres
        """
        with self._lock:
            values = list(self._workspaces.values())

        def predicate(w: Workspace) -> bool:
            if owner_user_id is not None and w.owner_user_id != owner_user_id:
                return False
            if not include_archived and self._is_archived(w):
                return False
            return True

        return self._sorted(w for w in values if predicate(w))

    def list_workspaces_by_visibility(
        self,
        visibility: WorkspaceVisibility,
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        Lista workspaces por visibilidad.

        Nota:
        - NO aplica políticas de RBAC; sólo filtra por valor de visibility.
        """
        with self._lock:
            values = list(self._workspaces.values())

        def predicate(w: Workspace) -> bool:
            if w.visibility != visibility:
                return False
            if not include_archived and self._is_archived(w):
                return False
            return True

        return self._sorted(w for w in values if predicate(w))

    def list_workspaces_by_ids(
        self,
        workspace_ids: List[UUID],
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        Lista workspaces por set explícito de IDs.

        Contrato:
        - [] si workspace_ids vacío
        - omite IDs inexistentes
        - respeta include_archived
        """
        if not workspace_ids:
            return []

        wanted = set(workspace_ids)

        with self._lock:
            candidates = [w for wid, w in self._workspaces.items() if wid in wanted]

        if not include_archived:
            candidates = [w for w in candidates if not self._is_archived(w)]

        return self._sorted(candidates)

    def list_workspaces_visible_to_user(
        self,
        user_id: UUID,
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        Lista workspaces "visibles" para un usuario.

        Importante (diseño):
        - En Postgres, la visibilidad SHARED se resuelve vía workspace_acl.
        - En memoria no tenemos ACL table, así que replicamos el contrato usando
          Workspace.shared_user_ids (campo de la entidad), para tests locales.

        Reglas que replica (sin ser “política completa”):
        - dueño => visible
        - ORG_READ => visible
        - SHARED => visible si user_id está en shared_user_ids
        """
        with self._lock:
            values = list(self._workspaces.values())

        def predicate(w: Workspace) -> bool:
            if not include_archived and self._is_archived(w):
                return False
            if w.owner_user_id == user_id:
                return True
            if w.visibility == WorkspaceVisibility.ORG_READ:
                return True
            if w.visibility == WorkspaceVisibility.SHARED:
                # shared_user_ids puede venir None: usamos copia defensiva
                return user_id in set(w.shared_user_ids or [])
            return False

        return self._sorted(w for w in values if predicate(w))

    # =========================================================
    # Lecturas puntuales
    # =========================================================
    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        """Obtiene workspace por ID (None si no existe)."""
        with self._lock:
            return self._workspaces.get(workspace_id)

    def get_workspace_by_owner_and_name(
        self,
        owner_user_id: UUID | None,
        name: str,
    ) -> Optional[Workspace]:
        """
        Obtiene workspace por (owner_user_id + name) para checks de unicidad.

        Nota:
        - Normaliza name (strip/lower) para comparación case-insensitive.
        - Si owner_user_id es None, retorna None (contrato coherente con Postgres).
        """
        if owner_user_id is None:
            return None

        normalized = self._normalize_name(name)
        with self._lock:
            for w in self._workspaces.values():
                if w.owner_user_id != owner_user_id:
                    continue
                if self._normalize_name(w.name) == normalized:
                    return w
        return None

    # =========================================================
    # Escrituras
    # =========================================================
    def create_workspace(self, workspace: Workspace) -> Workspace:
        """
        Crea workspace en memoria.

        Decisión:
        - Creamos una NUEVA instancia (no guardamos la referencia original)
          para evitar que el caller mutile el objeto y afecte el repo.
        - created_at/updated_at se setean aquí para consistencia.
        """
        now = self._now()

        created = Workspace(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            visibility=workspace.visibility,
            owner_user_id=workspace.owner_user_id,
            # Campos “de presentación/ACL” en memoria: copias defensivas
            allowed_roles=self._copy_roles(workspace.allowed_roles),
            shared_user_ids=self._copy_shared_ids(
                getattr(workspace, "shared_user_ids", None)
            ),
            created_at=now,
            updated_at=now,
            archived_at=workspace.archived_at,
        )

        with self._lock:
            self._workspaces[workspace.id] = created

        return created

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: WorkspaceVisibility | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Optional[Workspace]:
        """
        Actualiza atributos.

        Nota:
        - La semántica de allowed_roles puede diferir de Postgres (donde se guarda en documents).
          Aquí lo mantenemos porque la entidad lo expone y sirve para tests.
        """
        with self._lock:
            current = self._workspaces.get(workspace_id)
            if current is None:
                return None

            updated = Workspace(
                id=current.id,
                name=name if name is not None else current.name,
                description=(
                    description if description is not None else current.description
                ),
                visibility=visibility if visibility is not None else current.visibility,
                owner_user_id=current.owner_user_id,
                allowed_roles=(
                    self._copy_roles(allowed_roles)
                    if allowed_roles is not None
                    else self._copy_roles(current.allowed_roles)
                ),
                shared_user_ids=self._copy_shared_ids(
                    getattr(current, "shared_user_ids", None)
                ),
                created_at=current.created_at,
                updated_at=self._now(),
                archived_at=current.archived_at,
            )

            self._workspaces[workspace_id] = updated
            return updated

    def archive_workspace(self, workspace_id: UUID) -> bool:
        """
        Archiva workspace (soft-delete): setea archived_at + updated_at.

        Retorna:
        - False si no existe
        - True si existe (ya archivado o recién archivado)
        """
        with self._lock:
            current = self._workspaces.get(workspace_id)
            if current is None:
                return False
            if current.archived_at is not None:
                return True

            now = self._now()
            updated = Workspace(
                id=current.id,
                name=current.name,
                description=current.description,
                visibility=current.visibility,
                owner_user_id=current.owner_user_id,
                allowed_roles=self._copy_roles(current.allowed_roles),
                shared_user_ids=self._copy_shared_ids(
                    getattr(current, "shared_user_ids", None)
                ),
                created_at=current.created_at,
                updated_at=now,
                archived_at=now,
            )
            self._workspaces[workspace_id] = updated
            return True
