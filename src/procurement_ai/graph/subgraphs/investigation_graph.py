"""Investigation subgraph for multi-step evidence gathering."""

import logging

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)


def create_investigation_subgraph():
    """Create the investigation subgraph."""
    graph = StateGraph(dict)

    graph.add_node("plan", plan_node)
    graph.add_node("gather_evidence", gather_evidence_node)
    graph.add_node("compare", compare_node)
    graph.add_node("explain", explain_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "gather_evidence")
    graph.add_edge("gather_evidence", "compare")
    graph.add_edge("compare", "explain")
    graph.add_edge("explain", END)

    return graph.compile()


def plan_node(state: dict) -> dict:
    """Plan the investigation steps."""
    # TODO: Implement investigation planning
    state["investigation_plan"] = []
    return state


def gather_evidence_node(state: dict) -> dict:
    """Gather evidence from multiple sources."""
    # TODO: Implement evidence gathering with tool calls
    state["evidence"] = []
    return state


def compare_node(state: dict) -> dict:
    """Compare evidence across sources."""
    # TODO: Implement evidence comparison
    state["findings"] = []
    return state


def explain_node(state: dict) -> dict:
    """Generate explanation with citations."""
    # TODO: Implement explanation generation
    state["explanation"] = ""
    return state
