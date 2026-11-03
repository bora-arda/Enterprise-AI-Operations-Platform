"""Tool registry for agent tool discovery."""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_tools: dict[str, dict[str, Any]] = {}


def register_tool(name: str, description: str, func: Callable, requires_approval: bool = False):
    """Register a function as an agent tool."""
    _tools[name] = {
        "name": name,
        "description": description,
        "function": func,
        "requires_approval": requires_approval,
    }
    logger.info(f"Registered tool: {name}")


def get_tool(name: str) -> dict[str, Any] | None:
    """Get a tool by name."""
    return _tools.get(name)


def list_tools() -> list[dict[str, Any]]:
    """List all registered tools."""
    return list(_tools.values())


def clear_tools():
    """Clear all registered tools (for testing)."""
    _tools.clear()
