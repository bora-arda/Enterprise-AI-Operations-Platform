"""Idempotency key handling."""

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def generate_idempotency_key(tool_name: str, tool_args: dict) -> str:
    """Generate an idempotency key from tool name and arguments."""
    key_data = {"tool": tool_name, "args": tool_args}
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]


class IdempotencyStore:
    """Simple in-memory idempotency store."""

    def __init__(self):
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        return self._store.get(key)

    def set(self, key: str, result: Any) -> None:
        self._store[key] = result

    def clear(self) -> None:
        self._store.clear()


_idempotency_store = IdempotencyStore()


def check_idempotency(tool_name: str, tool_args: dict) -> tuple[bool, Any | None]:
    """Check if a tool call has been made before."""
    key = generate_idempotency_key(tool_name, tool_args)
    result = _idempotency_store.get(key)
    return result is not None, result


def store_idempotency_result(tool_name: str, tool_args: dict, result: Any) -> None:
    """Store the result of a tool call."""
    key = generate_idempotency_key(tool_name, tool_args)
    _idempotency_store.set(key, result)
