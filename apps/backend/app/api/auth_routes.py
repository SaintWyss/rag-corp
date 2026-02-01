"""
===============================================================================
TARJETA CRC — app/api/auth_routes.py (Autenticación y Administración de Usuarios)
===============================================================================

Responsabilidades:
  - Exponer endpoints de autenticación de usuario (login/logout/me) con JWT.
  - Gestionar cookie httpOnly (si está habilitada) de forma consistente.
  - Exponer endpoints administrativos para gestión de usuarios (crear/listar/desactivar/reset).
  - Emitir eventos de auditoría (best-effort) para acciones sensibles.

Patrones aplicados:
  - Adapter / Presentation Layer: traduce HTTP ↔ caso de uso/repositorio.
  - Fail-safe security: si la autenticación falla, se deniega por defecto.
  - Best-effort audit: auditoría no debe romper el flujo principal.

Colaboradores:
  - identity.auth_users: authenticate_user, create_access_token, require_user
  - identity.dual_auth: require_principal, require_admin
  - infrastructure.repositories.postgres.user: CRUD de usuarios (infra)
  - audit.emit_audit_event: persistencia best-effort
===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator

from ..audit import emit_audit_event
from ..container import get_audit_repository
from ..crosscutting.error_responses import (
    OPENAPI_ERROR_RESPONSES,
    conflict,
    not_found,
    unauthorized,
)
from ..domain.repositories import AuditEventRepository
from ..identity.auth_users import DEFAULT_ACCESS_TOKEN_COOKIE as ACCESS_TOKEN_COOKIE
from ..identity.auth_users import (
    authenticate_user,
    create_access_token,
    get_auth_settings,
    hash_password,
    require_user,
)
from ..identity.dual_auth import require_admin, require_principal
from ..identity.rbac import Permission
from ..identity.users import User, UserRole
from ..infrastructure.repositories.postgres.user import (
    create_user,
    get_user_by_email,
    list_users,
    set_user_active,
    update_user_password,
)

router = APIRouter(responses=OPENAPI_ERROR_RESPONSES)


# -----------------------------------------------------------------------------
# Modelos HTTP (DTOs)
# -----------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=512)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=512)
    role: UserRole = Field(default=UserRole.EMPLOYEE)
    is_active: bool = Field(default=True)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=512)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _to_user_response(user: User) -> UserResponse:
    """Convierte entidad de usuario a DTO de respuesta."""
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _set_auth_cookie(response: Response, token: str, expires_in: int) -> None:
    """Setea cookie httpOnly de acceso (si está configurada)."""
    settings = get_auth_settings()
    cookie_name = settings.jwt_cookie_name or ACCESS_TOKEN_COOKIE
    response.set_cookie(
        key=cookie_name,
        value=token,
        httponly=True,
        secure=settings.jwt_cookie_secure,
        samesite="lax",
        max_age=expires_in,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """Elimina cookie de acceso (si existe)."""
    settings = get_auth_settings()
    cookie_name = settings.jwt_cookie_name or ACCESS_TOKEN_COOKIE
    response.delete_cookie(
        key=cookie_name,
        path="/",
        samesite="lax",
        secure=settings.jwt_cookie_secure,
    )


# -----------------------------------------------------------------------------
# Endpoints públicos (login/logout/me)
# -----------------------------------------------------------------------------


@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(
    req: LoginRequest,
    response: Response,
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """
    Inicia sesión y devuelve JWT.

    - Si hay cookie habilitada, también setea cookie httpOnly.
    """
    user = authenticate_user(req.email, req.password)
    if not user:
        raise unauthorized("Credenciales inválidas.")

    token, expires_in = create_access_token(user)
    _set_auth_cookie(response, token, expires_in)

    emit_audit_event(
        audit_repo,
        action="auth.login",
        actor=f"user:{user.id}",
        target_id=user.id,
        metadata={"email": user.email, "role": user.role.value},
    )

    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=_to_user_response(user),
    )


@router.post("/auth/logout", tags=["auth"])
def logout(response: Response):
    """
    Cierra sesión.

    - Siempre borra la cookie (si estaba presente).
    - No requiere autenticación: es idempotente y seguro.
    """
    _clear_auth_cookie(response)
    return {"ok": True}


@router.get("/auth/me", response_model=UserResponse, tags=["auth"])
def me(user: User = Depends(require_user())):
    """Devuelve el usuario autenticado (JWT o cookie)."""
    return _to_user_response(user)


# -----------------------------------------------------------------------------
# Endpoints administrativos (usuarios)
# -----------------------------------------------------------------------------


@router.get("/auth/users", response_model=list[UserResponse], tags=["auth"])
def list_users_admin(
    limit: int = 200,
    offset: int = 0,
    principal=Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    """Lista usuarios (admin)."""
    users = list_users(limit=limit, offset=offset)
    return [_to_user_response(u) for u in users]


@router.post("/auth/users", response_model=UserResponse, status_code=201, tags=["auth"])
def create_user_admin(
    req: CreateUserRequest,
    principal=Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """Crea un usuario (admin)."""
    existing = get_user_by_email(req.email)
    if existing:
        raise conflict("El email ya existe.")

    user = create_user(
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        is_active=req.is_active,
    )

    emit_audit_event(
        audit_repo,
        action="admin.users.create",
        principal=principal,
        target_id=user.id,
        metadata={
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
        },
    )

    return _to_user_response(user)


@router.post(
    "/auth/users/{user_id}/disable",
    response_model=UserResponse,
    tags=["auth"],
)
def disable_user_admin(
    user_id: UUID,
    principal=Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """Desactiva un usuario (admin)."""
    user = set_user_active(user_id, False)
    if not user:
        raise not_found("User", str(user_id))

    emit_audit_event(
        audit_repo,
        action="admin.users.disable",
        principal=principal,
        target_id=user.id,
        metadata={"email": user.email, "role": user.role.value},
    )

    return _to_user_response(user)


@router.post(
    "/auth/users/{user_id}/reset-password",
    response_model=UserResponse,
    tags=["auth"],
)
def reset_password_admin(
    user_id: UUID,
    req: ResetPasswordRequest,
    principal=Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    """Resetea contraseña (admin)."""
    user = update_user_password(user_id, hash_password(req.password))
    if not user:
        raise not_found("User", str(user_id))

    emit_audit_event(
        audit_repo,
        action="admin.users.reset_password",
        principal=principal,
        target_id=user.id,
        metadata={"email": user.email, "role": user.role.value},
    )

    return _to_user_response(user)


__all__ = ["router"]
