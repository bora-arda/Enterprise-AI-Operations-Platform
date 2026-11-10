"""Small in-process TTL cache used for agent read-only lookups."""

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 512):
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_entries = max_entries
        self._items: dict[str, _Entry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._items.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if len(self._items) >= self.max_entries:
                # Drop the oldest/soonest-expiring entries first.
                for old_key, _ in sorted(self._items.items(), key=lambda item: item[1].expires_at)[
                    : max(1, self.max_entries // 8)
                ]:
                    self._items.pop(old_key, None)
            self._items[key] = _Entry(
                value=value,
                expires_at=time.monotonic() + self.ttl_seconds,
            )

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def get_agent_cache() -> TTLCache:
    from procurement_ai.config.settings import get_settings

    if not hasattr(get_agent_cache, "_cache"):
        get_agent_cache._cache = TTLCache(  # type: ignore[attr-defined]
            ttl_seconds=get_settings().agent_cache_ttl_seconds
        )
    return get_agent_cache._cache  # type: ignore[attr-defined, no-any-return]
