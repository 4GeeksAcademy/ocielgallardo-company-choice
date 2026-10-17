"""Idempotent registration of the agent service client (client-credentials).

Creates (or rotates) the secret of a machine identity such as
``svc:langgraph-agent`` and prints the plaintext secret **once**.

Usage:
    PYTHONPATH=. uv run python scripts/seed_service_client.py

Then set in the repo-root ``.env`` (gitignored, local dev):
    AGENT_TOOL_CLIENT_ID=langgraph-agent
    AGENT_TOOL_CLIENT_SECRET=<printed secret>

Re-running the script rotates the secret (previous secret stops working).
Scope is fixed to the two read-only tool routes of agent-graph.md §9.1.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

# Ensure repo root is importable when run as `python scripts/seed_service_client.py`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.app.core.service_identity import (  # noqa: E402
    DEFAULT_SERVICE_SCOPES,
    register_service_client,
)


def run_seed(client_id: str, secret: str | None = None) -> str:
    """Register/rotate the client; returns the plaintext secret to configure."""
    plaintext = secret or secrets.token_urlsafe(32)
    register_service_client(client_id, plaintext, DEFAULT_SERVICE_SCOPES)
    return plaintext


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register or rotate a HealthCore service client identity."
    )
    parser.add_argument(
        "--client-id",
        default="langgraph-agent",
        help="Service client id (default: langgraph-agent)",
    )
    parser.add_argument(
        "--secret",
        default=None,
        help="Optional explicit secret (default: random token_urlsafe)",
    )
    args = parser.parse_args()

    plaintext = run_seed(args.client_id, args.secret)
    print(f"Service client registered: svc:{args.client_id}")
    print(f"Scopes: {', '.join(DEFAULT_SERVICE_SCOPES)}")
    print("Plaintext secret (shown once, never commit it):")
    print(f"  AGENT_TOOL_CLIENT_ID={args.client_id}")
    print(f"  AGENT_TOOL_CLIENT_SECRET={plaintext}")
    print("Set them in the repo-root .env (gitignored) and recreate the backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
