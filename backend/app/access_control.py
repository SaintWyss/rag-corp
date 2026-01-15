"""
Name: Document Access Control

Responsibilities:
  - Enforce per-document access based on owner or allowed roles
"""

from __future__ import annotations

from .domain.entities import Document
from .dual_auth import Principal, PrincipalType
from .users import UserRole


def can_access_document(document: Document, principal: Principal | None) -> bool:
    if not principal or principal.principal_type == PrincipalType.SERVICE:
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
    allowed_roles = [role.lower() for role in (document.allowed_roles or [])]
    if not allowed_roles:
        return True
    return principal.user.role.value in allowed_roles


def filter_documents(
    documents: list[Document], principal: Principal | None
) -> list[Document]:
    return [doc for doc in documents if can_access_document(doc, principal)]
