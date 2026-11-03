"""FastAPI dependency injection."""

import logging

from fastapi import Request

from procurement_ai.database.connection import get_db_session

logger = logging.getLogger(__name__)


async def get_session(request: Request):
    """Get database session for the request."""
    async for session in get_db_session():
        yield session
