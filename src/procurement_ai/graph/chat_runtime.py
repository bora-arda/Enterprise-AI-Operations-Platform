"""Chat graph runtime with persistent conversation checkpoints."""

import asyncio
import logging

from procurement_ai.config.settings import get_settings
from procurement_ai.graph.action_execution import get_checkpointer
from procurement_ai.graph.orchestrator import create_orchestrator

logger = logging.getLogger(__name__)

_chat_graph = None
_lock = asyncio.Lock()


async def get_chat_graph():
    """Return the singleton chat graph backed by Postgres checkpoints."""
    global _chat_graph
    async with _lock:
        if _chat_graph is None:
            if get_settings().chat_memory_enabled:
                saver = await get_checkpointer()
                _chat_graph = create_orchestrator(checkpointer=saver)
                logger.info("Initialized chat graph with Postgres checkpointer")
            else:
                _chat_graph = create_orchestrator()
                logger.info("Chat memory disabled; using stateless graph")
    return _chat_graph


async def reset_chat_graph() -> None:
    """Drop the compiled graph (the shared checkpointer is managed elsewhere)."""
    global _chat_graph
    async with _lock:
        _chat_graph = None
