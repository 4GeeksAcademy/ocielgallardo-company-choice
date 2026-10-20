"""Shared fixtures for pipeline tests.

The graph can reach its tools over MCP when ``MCP_SERVER_URL`` is set (see
``data/pipelines/mcp_client.py``). Tests must not depend on the developer's
local ``.env`` — which the API modules load at import — or on a running MCP
server, so MCP transport is pinned off for this suite and every test keeps
exercising the direct-HTTP tool path deterministically.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(autouse=True)
def _disable_mcp_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_SERVER_URL", raising=False)
