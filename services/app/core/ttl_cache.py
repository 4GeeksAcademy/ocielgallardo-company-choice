"""In-process TTL cache for shared, non-session list responses.

Per-worker only: each uvicorn process holds its own dict. Prefer write-through
invalidation for freshness; TTL is a safety net if invalidation is skipped.
"""

from __future__ import annotations

import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TtlCache(Generic[T]):
    """Simple key → (expires_at, value) store with wall-clock TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: T, ttl_seconds: float) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)

    def invalidate(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Shared instance for inventory list endpoints (org-wide catalogs, not per-user).
inventory_list_cache: TtlCache[Any] = TtlCache()
