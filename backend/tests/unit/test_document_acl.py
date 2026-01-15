"""
Name: Document Access Control Tests

Responsibilities:
  - Validate per-document access rules for JWT principals
"""

from uuid import uuid4

import pytest

from app.access_control import can_access_document, filter_documents
from app.domain.entities import Document
from app.dual_auth import Principal, PrincipalType, ServicePrincipal, UserPrincipal
from app.users import UserRole


pytestmark = pytest.mark.unit


def _user_principal(role: UserRole, user_id=None) -> Principal:
    uid = user_id or uuid4()
    return Principal(
        principal_type=PrincipalType.USER,
        user=UserPrincipal(user_id=uid, email=f"{role.value}@example.com", role=role),
    )


def _service_principal() -> Principal:
    return Principal(
        principal_type=PrincipalType.SERVICE,
        service=ServicePrincipal(api_key_hash="hash", permissions=set()),
    )


def _doc(*, allowed_roles=None, owner_id=None) -> Document:
    return Document(
        id=uuid4(),
        title="Doc",
        uploaded_by_user_id=owner_id,
        allowed_roles=allowed_roles or [],
    )


def test_admin_can_access_any_document():
    principal = _user_principal(UserRole.ADMIN)
    document = _doc(allowed_roles=["employee"])

    assert can_access_document(document, principal) is True


def test_employee_can_access_owned_document():
    owner_id = uuid4()
    principal = _user_principal(UserRole.EMPLOYEE, user_id=owner_id)
    document = _doc(owner_id=owner_id, allowed_roles=["admin"])

    assert can_access_document(document, principal) is True


def test_employee_can_access_when_role_allowed():
    principal = _user_principal(UserRole.EMPLOYEE)
    document = _doc(allowed_roles=["employee"])

    assert can_access_document(document, principal) is True


def test_employee_denied_when_role_not_allowed():
    principal = _user_principal(UserRole.EMPLOYEE)
    document = _doc(allowed_roles=["admin"])

    assert can_access_document(document, principal) is False


def test_service_principal_bypasses_acl():
    principal = _service_principal()
    document = _doc(allowed_roles=["admin"])

    assert can_access_document(document, principal) is True


def test_filter_documents_applies_acl():
    employee = _user_principal(UserRole.EMPLOYEE)
    allowed = _doc(allowed_roles=["employee"])
    denied = _doc(allowed_roles=["admin"])

    result = filter_documents([allowed, denied], employee)
    assert result == [allowed]
