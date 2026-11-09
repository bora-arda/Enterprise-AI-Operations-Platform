"""Agent workflow node for the main LangGraph orchestrator."""

import logging

from procurement_ai.agent.loop import run_agent

logger = logging.getLogger(__name__)


async def agent_workflow_node(state: dict) -> dict:
    """Run the open-ended tool-calling agent."""
    result = await run_agent(
        question=state.get("user_input", ""),
        history=state.get("history", []),
        user_id=state.get("user_id"),
    )

    state["response"] = result.content
    state["citations"] = result.citations
    state["evidence"] = result.evidence
    state["tool_results"] = state.get("tool_results", []) + result.tool_results
    state["agent_trace"] = result.tool_trace
    state["confidence"] = 0.85
    state["workflow"] = "agent"
    state["intent"] = "analyze" if not state.get("intent") else state["intent"]
    logger.info(
        "Agent workflow completed: %s tool result(s), %s citation(s)",
        len(result.tool_results),
        len(result.citations),
    )
    return state
