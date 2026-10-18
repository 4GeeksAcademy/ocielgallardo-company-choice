"""Mint a HealthCore service token for manual use (MCP Playground, curl).

Exchanges a service client identity for a short-lived RS256 JWT via the API's
client-credentials grant (``POST /auth/token``) and prints the raw token on
stdout so it can be piped or pasted into the MCP Playground's Authorization
header. Human notes go to stderr.

Usage:
    PYTHONPATH=. uv run python scripts/mint_service_token.py
    PYTHONPATH=. uv run python scripts/mint_service_token.py \
        --client-id langgraph-agent \
        --audience https://<codespace>-8100.app.github.dev/mcp
    PYTHONPATH=. uv run python scripts/mint_service_token.py --no-audience

Credentials are read from the environment only (never hardcoded):
``<ENV_PREFIX>_CLIENT_ID`` and ``<ENV_PREFIX>_CLIENT_SECRET`` (or ``..._FILE``).

The audience MUST equal the MCP resource URL the server enforces (RFC 8707).
For a Codespaces Playground session set ``--audience`` to the public forwarded
URL of port 8100 (see ``docs/mcp/playground-codespaces.md``).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure repo root is importable when run as `python scripts/mint_service_token.py`
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx  # noqa: E402

DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_RESOURCE_URL = "http://localhost:8100/mcp"
TOKEN_TIMEOUT_SECONDS = 10.0


def _load_dotenv(path: Path) -> None:
    """Load ``KEY=VALUE`` lines from a .env file without overriding the shell.

    Keeps the script usable in Codespaces and local shells where the repo
    ``.env`` is not exported; existing environment variables always win.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


def _read_credential(name: str) -> str:
    """Credential from ``<name>_FILE`` (mounted secret) or plain env fallback."""
    file_path = os.getenv(f"{name}_FILE", "").strip()
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8").strip()
        except OSError:
            print(f"warning: could not read {name}_FILE={file_path}", file=sys.stderr)
    return os.getenv(name, "").strip()


def mint_token(
    *,
    client_id: str,
    client_secret: str,
    api_url: str,
    audience: str | None,
) -> tuple[str, float]:
    """Exchange credentials for a service token; returns ``(token, expires_in)``."""
    body = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if audience:
        body["audience"] = audience
    response = httpx.post(
        f"{api_url.rstrip('/')}/auth/token",
        json=body,
        timeout=TOKEN_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise SystemExit(
            f"grant rejected: HTTP {response.status_code} "
            f"(unknown client id, wrong secret, or API not running): "
            f"{response.text[:200]}"
        )
    payload = response.json()
    token = str(payload.get("access_token") or "")
    if not token:
        raise SystemExit("grant returned no access_token")
    return token, float(payload.get("expires_in") or 0)


def main() -> int:
    _load_dotenv(_ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Mint a HealthCore service token (client-credentials grant)."
    )
    parser.add_argument(
        "--env-prefix",
        default="AGENT_TOOL",
        help=(
            "Env var prefix holding the identity "
            "(default: AGENT_TOOL; reads <PREFIX>_CLIENT_ID / <PREFIX>_CLIENT_SECRET)"
        ),
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="Client id (default: <ENV_PREFIX>_CLIENT_ID from the environment)",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help=f"API base URL (default: AGENT_TOOL_API_URL or {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--audience",
        default=None,
        help=(
            "Token aud claim; MUST be the MCP resource URL "
            f"(default: MCP_RESOURCE_URL env or {DEFAULT_RESOURCE_URL})"
        ),
    )
    parser.add_argument(
        "--no-audience",
        action="store_true",
        help="Mint without an aud claim (only for callers that do not check it)",
    )
    args = parser.parse_args()

    client_id = args.client_id or _read_credential(f"{args.env_prefix}_CLIENT_ID")
    client_secret = _read_credential(f"{args.env_prefix}_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            f"missing credentials: set {args.env_prefix}_CLIENT_ID and "
            f"{args.env_prefix}_CLIENT_SECRET (or _FILE), or pass --client-id"
        )

    api_url = (
        args.api_url
        or os.getenv("AGENT_TOOL_API_URL", "").strip()
        or DEFAULT_API_URL
    )
    audience: str | None = None
    if not args.no_audience:
        audience = (
            args.audience
            or os.getenv("MCP_RESOURCE_URL", "").strip()
            or DEFAULT_RESOURCE_URL
        )

    token, expires_in = mint_token(
        client_id=client_id,
        client_secret=client_secret,
        api_url=api_url,
        audience=audience,
    )
    print(
        f"minted token for svc:{client_id} "
        f"(aud={audience or '<none>'}, expires_in={expires_in:.0f}s)",
        file=sys.stderr,
    )
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
