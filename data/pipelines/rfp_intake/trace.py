"""Append-only trace helpers for RFP Part 3 audit timeline.

Every node execution should record agent, input, output, and timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def make_trace_event(
    *,
    agent: str,
    action: str,
    department_id: str | None = None,
    detail: str | dict[str, Any] | None = None,
    input: Any = None,
    output: Any = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "department_id": department_id,
        "detail": detail if detail is not None else "",
        "input": input if input is not None else {},
        "output": output if output is not None else {},
    }
    return event


def append_events(
    existing: list[Any] | None,
    *events: dict[str, Any],
) -> list[dict[str, Any]]:
    out = [dict(e) for e in (existing or []) if isinstance(e, dict)]
    for event in events:
        out.append(dict(event))
    return out


__all__ = ["make_trace_event", "append_events"]
