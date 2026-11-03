"""Base agent class."""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str):
        self.name = name
        self.tools: list[dict] = []

    @abstractmethod
    async def run(self, state: dict) -> dict:
        """Execute the agent workflow."""
        pass

    def add_tool(self, tool: dict) -> None:
        """Add a tool to the agent's toolset."""
        self.tools.append(tool)

    def get_tools(self) -> list[dict]:
        """Get the agent's tools."""
        return self.tools
