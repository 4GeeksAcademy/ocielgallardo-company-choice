# MCP Playground validation from GitHub Codespaces

End-to-end runbook for the **hito 25** acceptance step: connect the MCP
Playground to the HealthCore MCP server through the **public URL forwarded by
Codespaces** (localhost does not work from the Playground site), run one full
flow per exposed tool, and capture the auth/error evidence.

## Prerequisites

- This repo opened in a Codespace (`.devcontainer/devcontainer.json` installs
  `uv`, syncs dependencies, and enables Docker-in-Docker).
- Root `.env` configured (copy from `.env.example`), including:
  - `MCP_BACKEND_CLIENT_ID` / `MCP_BACKEND_CLIENT_SECRET` (server identity)
  - `AGENT_TOOL_CLIENT_ID` / `AGENT_TOOL_CLIENT_SECRET` (agent identity)
  - Reachable database/backend settings (Supabase, see `.env.example`)
- Service identities registered (prints secrets once):
  ```bash
  PYTHONPATH=. uv run python scripts/seed_service_client.py \
      --client-id mcp-server --env-prefix MCP_BACKEND \
      --scopes incidents:read incidents:write inventory:read
  PYTHONPATH=. uv run python scripts/seed_service_client.py \
      --client-id langgraph-agent --env-prefix AGENT_TOOL
  ```

## 1. Use the public identity everywhere

The MCP resource URL is a **pure identifier**: it is the token `aud` (RFC 8707)
and the base for the RFC 9728 metadata the Playground's browser fetches. It
must be the public Codespaces URL:

```bash
# .env — replace <codespace> with your Codespace name
MCP_RESOURCE_URL=https://<codespace>-8100.app.github.dev/mcp
```

Everything internal stays internal:

```bash
MCP_AUTH_ISSUER_URL=http://backend:8000   # discovery fetch (compose)
MCP_AUTH_JWKS_URI=http://backend:8000/.well-known/jwks.json  # JWKS fetch
MCP_BACKEND_URL=http://backend:8000       # API base for the MCP server
MCP_SERVER_URL=http://mcp:8100/mcp        # agent → MCP endpoint (compose)
OAUTH_ISSUER_URL=http://localhost:8000    # `iss` claim identity of the API
```

Why the extra JWKS variable: discovery is announced by the API with the public
`iss` (`http://localhost:8000`) so tokens verify against a stable identity, but
the `mcp` container cannot resolve `localhost` to the API. `MCP_AUTH_JWKS_URI`
points only the JWKS download at the compose-network address, so `iss` stays
public and signature verification still works in-container.

## 2. Start the stack

```bash
docker compose up --build backend mcp
curl -fsS http://localhost:8100/health
```

Both containers read `MCP_RESOURCE_URL` from `.env`; restart `mcp` and `backend`
after changing it (env is baked at container start).

## 3. Publish port 8100

Codespaces → **Ports** → port `8100` → **Visibility: Public**. Copy the
forwarded URL: `https://<codespace>-8100.app.github.dev`.

## 4. Mint a Playground token

```bash
bash scripts/mcp_playground_runbook.sh mint \
  --audience https://<codespace>-8100.app.github.dev/mcp
# prints the raw JWT on stdout (notes go to stderr)
```

The audience is the token `aud` the server enforces; minting against
`http://localhost:8100/mcp` while the server is configured with the public URL
fails with `401 invalid_audience`.

## 5. Preflight (automated evidence)

```bash
MCP_PLAYGROUND_TOKEN=<token> \
MCP_SERVER_URL=https://<codespace>-8100.app.github.dev/mcp \
bash scripts/mcp_playground_runbook.sh preflight
```

Expected: health 200, PRM 200 with `authorization_servers`, `401` without a
token (with `WWW-Authenticate: Bearer … resource_metadata=…`), `401` for a
garbage token, `200` for `tools/list` with the minted token advertising the 6
tools.

## 6. MCP Playground session

1. Open the MCP Playground and add the server URL:
   `https://<codespace>-8100.app.github.dev/mcp` (public, not localhost).
2. Add the auth header `Authorization: Bearer <token>` in the Playground's
   header/auth field.
3. Confirm discovery lists the tools with descriptions and JSON schemas (no
   source code needed).

## 7. One full flow per tool (6/6)

| Tool | Example arguments | Expected |
| --- | --- | --- |
| `get_incident_status` | `{"ticket_id": 42}` | Ticket payload (status, category, branch…) or honest `not_found` |
| `list_incidents` | `{"status": "open"}` | Matching incidents list |
| `create_incident` | `{"title": "Playground check", "category": "it_system", "origin": "internal", "branch": "central", "description": "…"}` | New ticket created against the real Incidents Manager |
| `update_incident_status` | `{"ticket_id": <new id>, "status": "resolved"}` | Status updated via `PATCH /api/incidents/{id}/status` |
| `get_inventory_stock` | `{"sku": "HCR-PPE-001"}` | Stock payload |
| `update_inventory_stock` | `{"supply_id": 1, "quantity_change": 5, "reason": "playground"}` | **Controlled refusal** (see below) |

### Inventory write attempt (required by the rubric)

`update_inventory_stock` never touches the backend: it answers a contract
shaped refusal (`error="inventory_write_denied"`, `ok=false`) with the
read-only policy message. The audit log records it as a policy denial.

## 8. Auth/error evidence matrix

| Case | HTTP | Where it comes from |
| --- | --- | --- |
| No `Authorization` header | `401` `missing_auth_header` | MCP Auth bearer middleware |
| Malformed/garbage token | `401` `invalid_token` | JWT/JWKS validation |
| Token signed by another key (HS256 session token) | `401` `invalid_token` | JWKS lookup |
| Token `iss` ≠ discovery issuer | `401` `invalid_issuer` | Issuer validation |
| Token `aud` ≠ `MCP_RESOURCE_URL` | `401` `invalid_audience` | RFC 8707 audience check |
| Valid token, read-only scopes, write tool | Tool-level scope denial recorded as `denied_scope` in the audit log | `permissions.py` |

Run `bash scripts/mcp_playground_runbook.sh info` inside the Codespace for the
condensed step list.

## 9. Audit trail (tool/client/result per invocation)

```bash
docker compose logs mcp | grep mcp_tool
# mcp_tool tool=update_inventory_stock client=svc:langgraph-agent \
#   result=denied_policy ms=1.2
```

## 10. Agent side (single MCP path)

```bash
PYTHONPATH=. uv run python -c "from data.pipelines.agent_graph import run_agent; print(run_agent('What is the status of ticket 42?')['answer'])"
```

The agent mints its own token with `aud = MCP_RESOURCE_URL` and goes through
the MCP server only (no direct HTTP tool path exists anymore).

## Local environment caveat (antivirus HTTP interception)

Some endpoint-security products inspect plain-HTTP traffic on loopback and
rewrite responses for request paths ending in `/mcp`: they drop
`content-length` and add `transfer-encoding: chunked` without chunk framing, so
compliant clients fail with `chunk hex-length char not a hex digit: 0x7b` or
`RemoteProtocolError`. Observed on this dev machine with **Avast** Web Shield:
pausing its shields makes `curl http://localhost:8100/.../mcp` return the
expected `content-length` again.

Impact and options:

- Container-to-container traffic (agent inside compose → `http://mcp:8100/mcp`)
  is unaffected.
- Host-side clients (`curl`, the agent run from the terminal, the Playground on
  the Codespaces forward) need the antivirus to allow the endpoint. Add an
  exception for `localhost:8100`/`127.0.0.1:8100` in the antivirus Web Shield,
  or pause its shields while validating locally.

## Cleanup

- Rotate the pasted secret (it was exposed in a browser field on a public
  port): re-run `seed_service_client.py` with the same id and update `.env`.
- Set port 8100 back to **Private** when not validating.
