"""Database connection management.

The engine is created lazily and uses NullPool so that connections are not
reused across different event loops (important for FastAPI TestClient and
for clean shutdowns). Each request gets its own pooled-free connection.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from procurement_ai.config.settings import get_settings

logger = logging.getLogger(__name__)

_engine = None
_sessionmaker: async_sessionmaker | None = None


def get_engine():
    """Create the async engine on first use."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            poolclass=NullPool,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker:
    """Create the session factory on first use."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _sessionmaker


class _LazySessionFactory:
    """Callable that behaves like async_sessionmaker but is created lazily."""

    def __call__(self) -> AsyncSession:
        return get_sessionmaker()()


AsyncSessionLocal = _LazySessionFactory()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with get_sessionmaker()() as session:
        try:
            yield session
        finally:
            await session.close()
