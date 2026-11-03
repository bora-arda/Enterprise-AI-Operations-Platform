"""Detection workflow node.

Runs deterministic business rules against invoices in the database and
summarizes potential anomalies/policy violations.
"""

import logging
from collections import Counter

from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.observability.metrics import ANOMALIES_DETECTED
from procurement_ai.tools.detection_tools import detect_anomalies, detect_duplicates

logger = logging.getLogger(__name__)


async def detection_workflow_node(state: dict) -> dict:
    """Detect anomalies using deterministic rules."""
    question = state.get("user_input", "").lower()
    duplicate_mode = "duplicate" in question

    try:
        async with AsyncSessionLocal() as session:
            if duplicate_mode:
                anomalies = await detect_duplicates(session, limit=50000)
            else:
                anomalies = await detect_anomalies(session, entity_type="invoice", limit=2000)
    except Exception as e:
        logger.error(f"Detection failed: {e}", exc_info=True)
        state["response"] = "I encountered an error while running anomaly detection."
        state["errors"] = state.get("errors", []) + [str(e)]
        return state

    if not anomalies:
        state["response"] = (
            "No potential duplicate invoices were detected."
            if duplicate_mode
            else "No potential anomalies were detected in the analyzed invoice sample."
        )
        state["confidence"] = 0.7
        state["workflow"] = "detection"
        return state

    by_rule = Counter(a["rule"] for a in anomalies)
    for rule, count in by_rule.items():
        ANOMALIES_DETECTED.labels(type=rule).inc(count)

    header = (
        f"Detected {len(anomalies)} potential duplicate invoice groups:"
        if duplicate_mode
        else f"Analyzed invoices and detected {len(anomalies)} potential issues:"
    )
    lines = [header, ""]
    for rule, count in by_rule.most_common():
        lines.append(f"- {rule.replace('_', ' ')}: {count}")

    lines.append("")
    lines.append("Examples:")
    for anomaly in anomalies[:5]:
        lines.append(f"- {anomaly['description']} (severity: {anomaly['severity']})")

    citations = [
        {
            "source": f"rule:{a['rule']}",
            "snippet": a["description"],
        }
        for a in anomalies[:5]
    ]

    state["response"] = "\n".join(lines)
    state["citations"] = citations
    state["evidence"] = [
        {
            "source": f"rule:{a['rule']}",
            "content": a["description"],
            "metadata": a.get("details", {}),
        }
        for a in anomalies[:10]
    ]
    state["confidence"] = 0.85
    state["workflow"] = "detection"
    state["tool_results"] = state.get("tool_results", []) + [
        {
            "tool_name": "detect_anomalies",
            "success": True,
            "result": {"count": len(anomalies), "by_rule": dict(by_rule)},
            "error": None,
        }
    ]
    return state
