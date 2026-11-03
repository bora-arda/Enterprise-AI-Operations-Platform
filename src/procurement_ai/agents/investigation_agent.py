"""Investigation agent for multi-step evidence gathering."""

import logging

from procurement_ai.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class InvestigationAgent(BaseAgent):
    """Agent for multi-step investigations."""

    def __init__(self):
        super().__init__("investigation_agent")

    async def run(self, state: dict) -> dict:
        """Execute investigation workflow."""
        try:
            # TODO: Implement multi-step investigation
            state["evidence"] = []
            state["response"] = "Investigation agent executed (placeholder)."

        except Exception as e:
            logger.error(f"Investigation agent failed: {e}")
            state["errors"] = state.get("errors", []) + [str(e)]

        return state
