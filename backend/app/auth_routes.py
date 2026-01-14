"""
Name: Auth Routes (JWT)

Responsibilities:
  - Handle login/logout for user authentication
  - Expose /auth/me for current user info
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator

from .auth_users import (
    ACCESS_TOKEN_COOKIE,
    authenticate_user,
    create_access_token,
    get_auth_settings,
    hash_password,
    require_user,
)
from .dual_auth import require_admin, require_principal
from .error_responses import conflict, not_found, unauthorized
from .rbac import Permission
from .infrastructure.repositories.postgres_user_repo import (
    create_user,
    get_user_by_email,
    list_users,
    set_user_active,
    update_user_password,
)
from .users import User, UserRole

router = APIRouter()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=1, max_length=512)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
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


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


class UsersListResponse(BaseModel):
    users: list[UserResponse]


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=512)
    role: UserRole = Field(default=UserRole.EMPLOYEE)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=512)


def _set_auth_cookie(response: Response, token: str, expires_in: int) -> None:
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
    settings = get_auth_settings()
    cookie_name = settings.jwt_cookie_name or ACCESS_TOKEN_COOKIE
    response.delete_cookie(
        key=cookie_name,
        path="/",
        samesite="lax",
        secure=settings.jwt_cookie_secure,
    )


@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(req: LoginRequest, response: Response):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise unauthorized("Invalid credentials.")

    token, expires_in = create_access_token(user)
    _set_auth_cookie(response, token, expires_in)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=_to_user_response(user),
    )


@router.get("/auth/me", response_model=UserResponse, tags=["auth"])
def me(user: User = Depends(require_user())):
    return _to_user_response(user)


@router.post("/auth/logout", tags=["auth"])
def logout(response: Response):
    _clear_auth_cookie(response)
    return {"ok": True}


@router.get("/auth/users", response_model=UsersListResponse, tags=["auth"])
def list_users_admin(
    _: None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    users = list_users()
    return UsersListResponse(users=[_to_user_response(user) for user in users])


@router.post("/auth/users", response_model=UserResponse, status_code=201, tags=["auth"])
def create_user_admin(
    req: CreateUserRequest,
    _: None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    if get_user_by_email(req.email):
        raise conflict("User already exists.")
    user = create_user(
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        is_active=True,
    )
    return _to_user_response(user)


@router.post(
    "/auth/users/{user_id}/disable",
    response_model=UserResponse,
    tags=["auth"],
)
def disable_user_admin(
    user_id: UUID,
    _: None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    user = set_user_active(user_id, False)
    if not user:
        raise not_found("User", str(user_id))
    return _to_user_response(user)


@router.post(
    "/auth/users/{user_id}/reset-password",
    response_model=UserResponse,
    tags=["auth"],
)
def reset_password_admin(
    user_id: UUID,
    req: ResetPasswordRequest,
    _: None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    user = update_user_password(user_id, hash_password(req.password))
    if not user:
        raise not_found("User", str(user_id))
    return _to_user_response(user)
