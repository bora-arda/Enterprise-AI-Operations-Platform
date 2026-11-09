"""Planner decision audit endpoints."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.api.dependencies import get_db_session
from procurement_ai.api.schemas.decision import DecisionListResponse, DecisionResponse
from procurement_ai.auth.dependencies import AUDIT_ROLES, AuthUser, require_roles
from procurement_ai.database.models import PlannerDecisionRecord

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(row: PlannerDecisionRecord) -> DecisionResponse:
    return DecisionResponse(
        id=str(row.id),
        trace_id=row.trace_id,
        session_id=row.session_id,
        user_id=row.user_id,
        question=row.question,
        planner_mode=row.planner_mode,
        model=row.model,
        workflow=row.workflow,
        intent=row.intent,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        entity_name=row.entity_name,
        metric=row.metric,
        dimension=row.dimension,
        days=row.days,
        follow_up=row.follow_up or False,
        clarification_message=row.clarification_message,
        reason=row.reason,
        validation_result=row.validation_result,
        fallback_used=row.fallback_used or False,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        latency_ms=row.latency_ms,
        total_latency_ms=row.total_latency_ms,
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


@router.get("", response_model=DecisionListResponse)
async def list_decisions(
    trace_id: str | None = Query(None),
    session_id: str | None = Query(None),
    user_id: str | None = Query(None),
    workflow: str | None = Query(None),
    planner_mode: str | None = Query(None, pattern="^(llm|deterministic|agent_first)$"),
    fallback_used: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    _user: AuthUser = Depends(require_roles(*AUDIT_ROLES)),
):
    """List persisted planner/routing decisions with filters."""
    conditions = []
    if trace_id:
        conditions.append(PlannerDecisionRecord.trace_id == trace_id)
    if session_id:
        conditions.append(PlannerDecisionRecord.session_id == session_id)
    if user_id:
        conditions.append(PlannerDecisionRecord.user_id == user_id)
    if workflow:
        conditions.append(PlannerDecisionRecord.workflow == workflow)
    if planner_mode:
        conditions.append(PlannerDecisionRecord.planner_mode == planner_mode)
    if fallback_used is not None:
        conditions.append(PlannerDecisionRecord.fallback_used.is_(fallback_used))

    count_stmt = select(func.count()).select_from(PlannerDecisionRecord)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = await session.scalar(count_stmt) or 0

    stmt = select(PlannerDecisionRecord)
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(PlannerDecisionRecord.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    return DecisionListResponse(
        decisions=[_to_response(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
