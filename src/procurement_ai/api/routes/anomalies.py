"""Anomaly listing endpoints backed by the exceptions table."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.api.dependencies import get_db_session
from procurement_ai.api.schemas.anomaly import AnomalyListResponse, AnomalyResponse
from procurement_ai.auth.dependencies import AuthUser, get_current_user
from procurement_ai.database.models import Exception as ExceptionModel

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    severity: str | None = Query(None, pattern="^(low|medium|high)$"),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    user: AuthUser = Depends(get_current_user),
):
    """List detected anomalies with optional filtering."""
    query = select(ExceptionModel)

    if severity:
        query = query.where(ExceptionModel.severity == severity)
    if status:
        query = query.where(ExceptionModel.status == status)

    query = query.order_by(ExceptionModel.detected_at.desc()).limit(limit)

    result = await session.execute(query)
    rows = list(result.scalars().all())

    anomalies = [
        AnomalyResponse(
            id=str(row.id),
            invoice_id=str(row.invoice_id) if row.invoice_id else None,
            exception_type=row.exception_type or "unknown",
            severity=row.severity or "unknown",
            description=row.description or "",
            status=row.status or "open",
            detected_at=row.detected_at.isoformat() if row.detected_at else "",
        )
        for row in rows
    ]

    return AnomalyListResponse(anomalies=anomalies, total=len(anomalies))
