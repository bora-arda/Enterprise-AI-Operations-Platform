"""Authentication dependencies and role enforcement."""

import logging
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.api.dependencies import get_db_session
from procurement_ai.auth.security import decode_access_token
from procurement_ai.database.models import User

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

ALL_ROLES = {"specialist", "manager", "finance", "director", "admin"}
APPROVER_ROLES = {"manager", "finance", "director", "admin"}
AUDIT_ROLES = {"manager", "finance", "director", "admin"}


@dataclass
class AuthUser:
    id: str
    email: str
    name: str
    role: str
    department_id: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AuthUser:
    """Validate the bearer token and load the user from the database."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    subject = payload.get("sub")
    try:
        user_id = UUID(str(subject))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    if user.role not in ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role is not permitted",
        )

    return AuthUser(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        department_id=str(user.department_id) if user.department_id else None,
    )


def require_roles(*roles: str):
    """Dependency factory: require one of the given roles."""
    allowed = set(roles)

    async def _checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized for this operation",
            )
        return user

    return _checker
