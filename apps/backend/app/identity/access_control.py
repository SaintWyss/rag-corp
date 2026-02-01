"""
===============================================================================
TARJETA CRC — identity/access_control.py
===============================================================================

Módulo:
    Control de Acceso a Documentos (Policy Helper)

Responsabilidades:
    - Encapsular la política de acceso a un Document según un Principal.
    - Proveer helpers para filtrar listados de documentos.

Colaboradores:
    - domain.entities.Document: datos del documento (owner + allowed_roles).
    - identity.dual_auth.Principal: sujeto autenticado (USER o SERVICE).
    - identity.users.UserRole: roles (admin, employee).

Notas:
    - Este módulo NO depende de FastAPI. Es lógica pura (fácil de testear).
    - La decisión “default allow” se mantiene para no romper entornos sin auth.
      Los endpoints críticos deben seguir usando dependencias de auth/permissions.
===============================================================================
"""

from __future__ import annotations

from ..domain.entities import Document
from .dual_auth import Principal, PrincipalType
from .users import UserRole


def can_access_document(document: Document, principal: Principal | None) -> bool:
    """True si el principal puede acceder al documento.

    Regla general:
        - Si no hay principal (auth deshabilitada): permitir.
        - SERVICE (API key): permitir (se asume autorización por endpoint/permisos).
        - USER admin: permitir.
        - USER dueño del documento: permitir.
        - Si el documento no define allowed_roles: permitir.
        - Si define allowed_roles: permitir si el rol del user está incluido.
    """
    if not principal:
        return True

    if principal.principal_type == PrincipalType.SERVICE:
        return True

    if not principal.user:
        return True

    if principal.user.role == UserRole.ADMIN:
        return True

    if (
        document.uploaded_by_user_id
        and document.uploaded_by_user_id == principal.user.user_id
    ):
        return True

    allowed_roles = [
        str(r).strip().lower() for r in (document.allowed_roles or []) if str(r).strip()
    ]
    if not allowed_roles:
        return True

    return principal.user.role.value in allowed_roles


def filter_documents(
    documents: list[Document], principal: Principal | None
) -> list[Document]:
    """Filtra documentos aplicando la policy can_access_document."""
    return [doc for doc in documents if can_access_document(doc, principal)]
