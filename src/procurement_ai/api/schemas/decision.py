"""Planner decision audit schemas."""

from pydantic import BaseModel


class DecisionResponse(BaseModel):
    id: str
    trace_id: str
    session_id: str | None = None
    user_id: str | None = None
    question: str
    planner_mode: str
    model: str | None = None
    workflow: str | None = None
    intent: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None
    metric: str | None = None
    dimension: str | None = None
    days: int | None = None
    follow_up: bool = False
    clarification_message: str | None = None
    reason: str | None = None
    validation_result: str
    fallback_used: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    total_latency_ms: int | None = None
    created_at: str


class DecisionListResponse(BaseModel):
    decisions: list[DecisionResponse]
    total: int
    limit: int
    offset: int
