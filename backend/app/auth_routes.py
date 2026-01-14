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
    require_user,
)
from .error_responses import unauthorized
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
