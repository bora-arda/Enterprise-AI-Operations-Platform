"""Chat endpoint for natural language interaction."""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from procurement_ai.api.schemas.chat import ChatRequest, ChatResponse, Citation
from procurement_ai.auth.dependencies import AuthUser, get_current_user
from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import PlannerDecisionRecord
from procurement_ai.graph.chat_runtime import get_chat_graph
from procurement_ai.observability.metrics import (
    TOOL_CALLS,
    TOOL_ERRORS,
    WORKFLOW_COUNT,
    WORKFLOW_DURATION,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Main conversation endpoint.

    Runs the LangGraph orchestrator with a persistent thread per session:
    guardrails -> intent routing -> workflow -> response validation.
    """
    trace_id = str(uuid.uuid4())[:8]
    session_id = request.session_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "user_input": request.message,
        "user_id": user.id,
        "session_id": session_id,
        "history": [],
        "intent": "",
        "workflow": "",
        "planned_route": None,
        "evidence": [],
        "citations": [],
        "tool_calls": [],
        "tool_results": [],
        "action_request": None,
        "approval_status": "not_required",
        "approval_decision": None,
        "response": "",
        "confidence": None,
        "errors": [],
        "trace_id": trace_id,
        "node_latencies": {},
    }

    start = time.perf_counter()
    try:
        graph = await get_chat_graph()

        # Load prior conversation memory for this session (if enabled)
        try:
            previous = await graph.aget_state(config)
        except Exception:
            previous = None
        previous_values = previous.values if previous else {}
        history = list(previous_values.get("history", []))[-8:]
        history.append({"role": "user", "content": request.message})
        initial_state["history"] = history
        if previous_values.get("last_invoice_number"):
            initial_state["last_invoice_number"] = previous_values["last_invoice_number"]

        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    duration = time.perf_counter() - start

    workflow = final_state.get("workflow") or final_state.get("intent") or "unknown"
    intent = final_state.get("intent") or "unknown"
    WORKFLOW_COUNT.labels(workflow=workflow, intent=intent).inc()
    WORKFLOW_DURATION.labels(workflow=workflow).observe(duration)

    for tool_result in final_state.get("tool_results", []):
        tool_name = tool_result.get("tool_name", "unknown")
        TOOL_CALLS.labels(tool=tool_name).inc()
        if not tool_result.get("success", True):
            TOOL_ERRORS.labels(tool=tool_name).inc()

    # Persist the routing decision for audit and debugging.
    audit = final_state.get("planner_audit") or {}
    planned = final_state.get("planned_route") or {}
    decision_id: str | None = str(uuid.uuid4())

    try:
        async with AsyncSessionLocal() as session:
            session.add(
                PlannerDecisionRecord(
                    id=uuid.UUID(decision_id),
                    trace_id=trace_id,
                    session_id=session_id,
                    user_id=user.id,
                    question=request.message,
                    planner_mode=audit.get("planner_mode", "unknown"),
                    model=audit.get("model"),
                    workflow=final_state.get("workflow"),
                    intent=final_state.get("intent"),
                    entity_type=planned.get("entity_type"),
                    entity_id=planned.get("entity_id"),
                    entity_name=planned.get("entity_name"),
                    metric=planned.get("metric"),
                    dimension=planned.get("dimension"),
                    days=planned.get("days"),
                    follow_up=bool(planned.get("follow_up")),
                    clarification_message=(
                        planned.get("clarification_message") or final_state.get("clarification_message") or None
                    ),
                    reason=planned.get("reason"),
                    raw_decision=audit.get("raw_decision"),
                    validation_result=audit.get("validation_result", "unknown"),
                    fallback_used=bool(audit.get("fallback_used")),
                    input_tokens=audit.get("input_tokens"),
                    output_tokens=audit.get("output_tokens"),
                    latency_ms=audit.get("latency_ms"),
                    total_latency_ms=int(duration * 1000),
                )
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to persist planner decision: {e}", exc_info=True)
        decision_id = None

    citations = [
        Citation(source=c.get("source", ""), snippet=c.get("snippet", "")) for c in final_state.get("citations", [])
    ]

    return ChatResponse(
        response=final_state.get("response") or "I couldn't produce an answer for that question.",
        citations=citations,
        confidence=final_state.get("confidence"),
        workflow=final_state.get("workflow") or final_state.get("intent"),
        trace_id=trace_id,
        decision_id=decision_id,
    )
