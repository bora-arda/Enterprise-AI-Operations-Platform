"""Authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.api.dependencies import get_db_session
from procurement_ai.auth.dependencies import AuthUser, get_current_user
from procurement_ai.auth.security import create_access_token, verify_password
from procurement_ai.config.settings import get_settings
from procurement_ai.database.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class UserInfo(BaseModel):
    id: str
    email: str
    name: str
    role: str
    department_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserInfo


def _user_info(user: AuthUser) -> UserInfo:
    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        department_id=user.department_id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Exchange email/password for a JWT access token."""
    result = await session.execute(select(User).where(func.lower(User.email) == payload.email.lower().strip()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
    )
    settings = get_settings()
    logger.info(f"Login succeeded for {user.email} ({user.role})")

    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.access_token_expire_minutes,
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            department_id=str(user.department_id) if user.department_id else None,
        ),
    )


@router.get("/me", response_model=UserInfo)
async def me(user: AuthUser = Depends(get_current_user)):
    """Return the authenticated user."""
    return _user_info(user)
