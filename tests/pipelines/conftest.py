"""Shared fixtures for pipeline tests.

The graph can reach its tools over MCP when ``MCP_SERVER_URL`` is set (see
``data/pipelines/mcp_client.py``). Tests must not depend on the developer's
local ``.env`` — which the API modules load at import — or on a running MCP
server, so MCP transport is pinned off for this suite and every test keeps
exercising the direct-HTTP tool path deterministically. The agent-memory
loop (hito 26) is pinned to the in-process store with its LLM seams stubbed,
so only the memory-specific suites drive proposals end to end.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import data.pipelines.agent_memory as agent_memory  # noqa: E402
import data.pipelines.memory_proposer as memory_proposer  # noqa: E402


@pytest.fixture(autouse=True)
def _disable_mcp_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)


@pytest.fixture(autouse=True)
def _offline_memory(monkeypatch: pytest.MonkeyPatch):
    """Pin the memory loop off the network.

    In-process store, no Redis and no LLM in the memory steps, so suites that
    do not study memory keep their original behaviour (a proposal is never
    raised and a pending proposal classifies as ``unrelated``). Tests that
    exercise memory override these seams with their own spies.
    """
    monkeypatch.setenv("AGENT_MEMORY_BACKEND", "memory")
    monkeypatch.setattr(
        memory_proposer, "propose_from_interaction", lambda question, answer: None
    )
    monkeypatch.setattr(
        memory_proposer,
        "classify_decision",
        lambda proposal, message: {"label": "unrelated", "edited_fact": None},
    )
    agent_memory.reset_store()
    yield
    agent_memory.reset_store()
