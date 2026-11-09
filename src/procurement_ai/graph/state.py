"""LangGraph state definitions."""

from typing import Any, Literal, TypedDict


class Evidence(TypedDict):
    source: str
    content: str
    metadata: dict[str, Any]


class Citation(TypedDict):
    source: str
    snippet: str


class ToolCall(TypedDict):
    tool_name: str
    tool_args: dict[str, Any]


class ToolResult(TypedDict):
    tool_name: str
    success: bool
    result: Any
    error: str | None


class ActionRequest(TypedDict):
    action_type: str
    entity_id: str
    params: dict[str, Any]
    justification: str


class ApprovalDecision(TypedDict):
    decision: Literal["approve", "reject"]
    comment: str | None
    decided_by: str
    decided_at: str


class AgentState(TypedDict):
    # Input
    user_input: str
    user_id: str
    session_id: str

    # Conversation memory
    history: list[dict]
    last_invoice_number: str | None

    # Routing
    intent: str
    workflow: str
    planned_route: dict | None
    previous_route: dict | None
    planner_audit: dict | None

    # Evidence
    evidence: list[Evidence]
    citations: list[Citation]

    # Tool calls
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]

    # Action workflow
    action_request: ActionRequest | None
    approval_status: Literal["pending", "approved", "rejected", "not_required"]
    approval_decision: ApprovalDecision | None

    # Clarification
    clarification_needed: bool
    clarification_message: str

    # Output
    response: str
    confidence: float | None
    errors: list[str]

    # Observability
    trace_id: str
    node_latencies: dict[str, float]
