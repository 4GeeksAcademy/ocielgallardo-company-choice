"""In-process sliding-window rate limiter for LLM-facing endpoints.

Limits are env-driven so production can tighten without code changes.
Defaults favor local/dev usability while still making cost abuse visible.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0
    limit: int = 0
    window_seconds: int = 0


class SlidingWindowRateLimiter:
    """Thread-safe sliding window of timestamps per key."""

    def __init__(
        self,
        *,
        max_calls: int | None = None,
        window_seconds: float | None = None,
    ) -> None:
        # Defaults match AGENT_QUERY_* env when constructed without args (unit tests).
        resolved_max = (
            max_calls if max_calls is not None else _env_int("AGENT_QUERY_RATE_LIMIT", 20)
        )
        resolved_window = (
            window_seconds
            if window_seconds is not None
            else float(_env_int("AGENT_QUERY_RATE_WINDOW_SECONDS", 60))
        )
        if resolved_max < 1:
            raise ValueError("max_calls must be >= 1")
        if resolved_window <= 0:
            raise ValueError("window_seconds must be > 0")
        self.max_calls = int(resolved_max)
        self.window_seconds = float(resolved_window)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def check(
        self,
        key: str,
        *,
        limit: int | None = None,
        window_seconds: float | None = None,
        now: float | None = None,
    ) -> RateLimitDecision:
        """Return a decision; optional per-call limit/window override for tests."""
        max_calls = int(limit) if limit is not None else self.max_calls
        window = float(window_seconds) if window_seconds is not None else self.window_seconds
        if max_calls < 1:
            raise ValueError("limit must be >= 1")
        if window <= 0:
            raise ValueError("window_seconds must be > 0")

        ts = time.monotonic() if now is None else now
        with self._lock:
            bucket = self._hits[key]
            cutoff = ts - window
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= max_calls:
                retry_after = max(1.0, bucket[0] + window - ts)
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=int(retry_after) if retry_after >= 1 else 1,
                    limit=max_calls,
                    window_seconds=int(window),
                )
            bucket.append(ts)
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
                limit=max_calls,
                window_seconds=int(window),
            )


def agent_query_limiter_from_env() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(
        max_calls=_env_int("AGENT_QUERY_RATE_LIMIT", 20),
        window_seconds=float(_env_int("AGENT_QUERY_RATE_WINDOW_SECONDS", 60)),
    )


# Process-wide limiter for POST /agent/query (tests may reset).
agent_query_limiter = agent_query_limiter_from_env()


def check_agent_query_rate(key: str) -> RateLimitDecision:
    """Evaluate the per-user agent query budget using current env-backed limiter settings.

    Reloads limit/window from env on each call so tests can ``monkeypatch.setenv``
    without reconstructing the singleton.
    """
    limit = _env_int("AGENT_QUERY_RATE_LIMIT", 20)
    window = _env_int("AGENT_QUERY_RATE_WINDOW_SECONDS", 60)
    return agent_query_limiter.check(key, limit=limit, window_seconds=window)


def enforce_agent_query_rate_limit(key: str) -> None:
    """Raise ``HTTPException`` 429 when the caller exceeds the agent query budget."""
    from fastapi import HTTPException, status

    decision = check_agent_query_rate(key)
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Agent query rate limit exceeded. Try again shortly.",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )
