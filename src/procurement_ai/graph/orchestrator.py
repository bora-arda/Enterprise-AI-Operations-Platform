"""Main LangGraph orchestrator with integrated workflow nodes."""

import asyncio
import functools
import logging
import time
from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from procurement_ai.graph.nodes.action import action_workflow_node
from procurement_ai.graph.nodes.clarify import clarify_node
from procurement_ai.graph.nodes.detection import detection_workflow_node
from procurement_ai.graph.nodes.guardrails import guardrails_node
from procurement_ai.graph.nodes.intent import intent_classifier_node
from procurement_ai.graph.nodes.investigation import investigation_workflow_node
from procurement_ai.graph.nodes.planner import planner_node
from procurement_ai.graph.nodes.retrieval import retrieval_workflow_node
from procurement_ai.graph.nodes.sql import sql_workflow_node
from procurement_ai.graph.nodes.validation import response_validator_node
from procurement_ai.graph.state import AgentState
from procurement_ai.observability.metrics import NODE_DURATION

logger = logging.getLogger(__name__)


def _timed(name: str, fn: Callable) -> Callable:
    """Wrap a node to record its execution time in Prometheus."""
    if asyncio.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(state):
            start = time.perf_counter()
            try:
                return await fn(state)
            finally:
                NODE_DURATION.labels(node=name).observe(time.perf_counter() - start)

        return async_wrapper

    @functools.wraps(fn)
    def wrapper(state):
        start = time.perf_counter()
        try:
            return fn(state)
        finally:
            NODE_DURATION.labels(node=name).observe(time.perf_counter() - start)

    return wrapper


def create_orchestrator(checkpointer=None):
    """Create the main orchestration graph with all workflow nodes."""
    graph = StateGraph(AgentState)

    # Add nodes (instrumented for per-node latency metrics)
    graph.add_node("guardrails", _timed("guardrails", guardrails_node))
    graph.add_node("planner", _timed("planner", planner_node))
    graph.add_node("intent_classifier", _timed("intent_classifier", intent_classifier_node))
    graph.add_node("retrieval_workflow", _timed("retrieval_workflow", retrieval_workflow_node))
    graph.add_node("sql_workflow", _timed("sql_workflow", sql_workflow_node))
    graph.add_node("investigation_workflow", _timed("investigation_workflow", investigation_workflow_node))
    graph.add_node("detection_workflow", _timed("detection_workflow", detection_workflow_node))
    graph.add_node("action_workflow", _timed("action_workflow", action_workflow_node))
    graph.add_node("clarify", _timed("clarify", clarify_node))
    graph.add_node("response_validator", _timed("response_validator", response_validator_node))
    graph.add_node("fallback", _timed("fallback", fallback_node))

    # Add edges
    graph.add_edge(START, "guardrails")
    graph.add_conditional_edges(
        "guardrails",
        route_after_guardrails,
        {
            "pass": "planner",
            "fail": "fallback",
        },
    )
    graph.add_edge("planner", "intent_classifier")
    graph.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "find": "retrieval_workflow",
            "understand": "retrieval_workflow",
            "query": "sql_workflow",
            "analyze": "sql_workflow",
            "investigate": "investigation_workflow",
            "detect": "detection_workflow",
            "act": "action_workflow",
            "clarify": "clarify",
            "out_of_scope": "fallback",
        },
    )

    # All workflows lead to response validation
    for workflow in [
        "retrieval_workflow",
        "sql_workflow",
        "investigation_workflow",
        "detection_workflow",
        "action_workflow",
        "clarify",
    ]:
        graph.add_edge(workflow, "response_validator")

    graph.add_edge("response_validator", END)
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=checkpointer)


def route_after_guardrails(state: AgentState) -> str:
    """Route after guardrails check."""
    errors = state.get("errors", [])
    if errors:
        return "fail"
    return "pass"


def route_after_intent(state: AgentState) -> str:
    """Route based on classified intent, preferring clarification when needed."""
    if state.get("clarification_needed"):
        return "clarify"
    return state.get("intent", "out_of_scope")


def fallback_node(state: AgentState) -> AgentState:
    """Handle errors and unsupported requests."""
    logger.info("Running fallback handler")
    if not state.get("response"):
        state["response"] = (
            "I'm designed to help with procurement and finance operations. "
            "I can help you investigate invoices, purchase orders, contracts, "
            "payments, and procurement policies. Could you rephrase your question "
            "in that context?"
        )
    return state
