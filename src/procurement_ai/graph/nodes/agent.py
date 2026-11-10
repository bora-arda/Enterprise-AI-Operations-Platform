"""Agent workflow node for the main LangGraph orchestrator."""

import logging

from procurement_ai.agent.loop import run_agent
from procurement_ai.security.access import scope_from_state

logger = logging.getLogger(__name__)


async def agent_workflow_node(state: dict) -> dict:
    """Run the open-ended tool-calling agent within the caller's access scope."""
    result = await run_agent(
        question=state.get("user_input", ""),
        history=state.get("history", []),
        user_id=state.get("user_id"),
        scope=scope_from_state(state),
    )

    state["response"] = result.content
    state["citations"] = result.citations
    state["evidence"] = result.evidence
    state["tool_results"] = state.get("tool_results", []) + result.tool_results
    state["agent_trace"] = result.tool_trace
    state["verification"] = result.verification
    state["request_cost_usd"] = result.cost_usd
    state["request_input_tokens"] = result.input_tokens
    state["request_output_tokens"] = result.output_tokens
    state["request_tool_errors"] = result.tool_errors
    state["agent_model"] = result.model
    state["confidence"] = 0.78 if result.verification.get("status") == "warnings" else 0.85
    state["workflow"] = "agent"
    state["intent"] = "analyze" if not state.get("intent") else state["intent"]
    logger.info(
        "Agent workflow completed: %s tool result(s), %s citation(s)",
        len(result.tool_results),
        len(result.citations),
    )
    return state
