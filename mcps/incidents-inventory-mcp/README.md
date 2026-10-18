# Incidents + inventory MCP server

OAuth-protected **Model Context Protocol** server that exposes the HealthCore
operational tools the support agent needs: incident lookups and writes, and
read-only inventory stock lookups. It is a standalone process (compose service
`mcp`, port `8100`) in front of the existing API — no new data paths, no new
business rules.

> _Spanish version: [README.es.md](./README.es.md)._

## Tools and scopes

| Tool | Arguments | Scope | Notes |
|------|-----------|-------|-------|
| `get_incident_status` | `ticket_id` | `incidents:read` | One incident by id |
| `list_incidents` | `status`, `origin`, `branch`, `category` (at least one) | `incidents:read` | Exact-match filters |
| `create_incident` | `title`, `description`, `category`, `origin`, `branch` | `incidents:write` | API validates the enums |
| `update_incident_status` | `ticket_id`, `status` | `incidents:write` | API validates the transition |
| `get_inventory_stock` | `supply_id` or `sku` or `name_query` | `inventory:read` | Read-only stock lookups |
| `update_inventory_stock` | `supply_id`, `quantity_change`, `reason` | — | **Always refuses** (`inventory_write_denied`); never touches the backend |

Every result uses the agent's existing contracts (`IncidentToolOutput` /
`InventoryToolOutput` from `data/pipelines/agent_tools.py`): `ok`, payload, and
`error` ∈ `not_found | timeout | unavailable | invalid_input | auth`. Failures
are reported as tool data, never as invented state. Return types are annotated
(`structured_output=True`), so `tools/list` advertises an `outputSchema` and
successful calls answer with `structuredContent`.

## Security model

- **OAuth resource server (RFC 9728) via MCP Auth (`mcpauth`).** `/mcp`
  requires a bearer token; `401`/`403` answers carry
  `WWW-Authenticate: … resource_metadata="…"` and the metadata is served at
  `/.well-known/oauth-protected-resource/mcp`, pointing authorization at the
  HealthCore API (`MCP_AUTH_ISSUER_URL`).
- **Token validation.** MCP Auth fetches the issuer's
  `/.well-known/openid-configuration` at startup and verifies each token
  against that issuer's JWKS (RS256): `iss` must equal the issuer and `aud`
  must equal this resource (`MCP_RESOURCE_URL`, RFC 8707). Only RS256 tokens
  minted by the API's client-credentials grant can validate; human session
  tokens (HS256) cannot. No shared symmetric secret in this process.
- **Per-tool authorization.** MCP Auth stores the verified identity
  (`AuthInfo`: subject, client_id, scopes) in a context variable; each tool
  then asserts its own scope (`permissions.require_scopes`), fail-closed when
  the identity is absent. Denials are explicit tool errors
  (`insufficient_scope: missing …`), not silent failures.
- **Identity towards the API.** The server re-authenticates with its own
  service identity (`MCP_BACKEND_CLIENT_ID` / `MCP_BACKEND_CLIENT_SECRET`,
  optionally `…_FILE`), so an MCP caller can never write with a scope it was
  not granted. Inventory is read-only in five layers: a refusal tool
  (`update_inventory_stock` → `inventory_write_denied`), the scope gate, a
  GET-only endpoint allowlist in `backend_client`, no write helpers in the
  server module, and human-only write routes in the API.
- **Audited.** Every tool call logs `tool= client= result= ms=`, including
  scope and read-only denials (`result=denied_scope` / `result=denied_policy`).

## Error catalog

Transport level (before any tool runs; OAuth error codes in the JSON body and
in `WWW-Authenticate`):

| Code | HTTP | Meaning |
|------|------|---------|
| `missing_auth_header` | 401 | No `Authorization` header |
| `invalid_auth_header_format` | 401 | Header is not `Bearer <token>` |
| `missing_bearer_token` | 401 | `Bearer` with an empty token |
| `invalid_token` | 401 | Bad signature, expired, malformed, or not verifiable against the issuer JWKS |
| `invalid_issuer` | 401 | Token `iss` is not the configured authorization server |
| `invalid_audience` | 401 | Token `aud` is not this resource (`MCP_RESOURCE_URL`) |

Tool level (valid token, authorization or contract outcome):

| Marker | Where | Meaning |
|--------|-------|---------|
| `insufficient_scope: missing <scope>` | tool error (`isError`) | Token lacks the scope the tool requires |
| `inventory_write_denied` | tool error (`isError`) | Explicit read-only refusal from `update_inventory_stock` |
| `not_found` / `timeout` / `unavailable` / `invalid_input` / `auth` | contract payload (`ok: false`) | Backend outcome reported as data, not as a protocol error |
| `Unknown tool` | tool error | Tool name not registered |

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `MCP_AUTH_ISSUER_URL` | Authorization server whose discovery document is fetched at startup | `http://localhost:8000` |
| `MCP_AUTH_JWKS_URI` | Optional override for the discovery document's `jwks_uri` (compose points it at `http://backend:8000/.well-known/jwks.json`) | advertised value |
| `MCP_RESOURCE_URL` | This resource's identity; also the required token `aud` | `http://localhost:8100/mcp` |
| `MCP_BACKEND_URL` | API base URL | `http://127.0.0.1:8000` |
| `MCP_BACKEND_CLIENT_ID` / `_SECRET` / `_SECRET_FILE` | Server's own service identity | — |
| `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` | DNS-rebinding allowlists (defaults cover loopback, `mcp`, `testserver`, `*.github.dev`) | — |

All values come from the environment (Compose passes `.env`); the server never
stores credentials. The issuer must be reachable when the app builds (startup
fetch). `MCP_AUTH_JWKS_URI` exists for deployments where discovery advertises a
JWKS URL that this process cannot resolve (compose: the `mcp` container reaches
the API as `backend`, not `localhost`), while token `iss` must stay the public
issuer. `SECRET_KEY` is **not** used by this process.

## Run

Local (from the repo root, API already running on `:8000`):

```bash
PYTHONPATH=. uv run uvicorn incidents_inventory_mcp.app:app \
    --app-dir mcps/incidents-inventory-mcp --port 8100
```

Register/rotate the server identity (prints the secret once):

```bash
PYTHONPATH=. uv run python scripts/seed_service_client.py \
    --client-id mcp-server --env-prefix MCP_BACKEND \
    --scopes incidents:read incidents:write inventory:read
```

Compose (same image as the backend, in-network URLs):

```bash
docker compose up --build mcp     # health: curl http://localhost:8100/health
```

## Connect a client

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "healthcore": {
        "transport": "streamable_http",
        "url": "http://127.0.0.1:8100/mcp",
        "headers": {"Authorization": f"Bearer {service_token}"},
    }
})
tools = await client.get_tools()          # 6 tools
result = await tools[0].ainvoke({...})
```

The token must be minted with `aud` equal to the resource URL
(`POST /auth/token` accepts an `audience` field). A client without a valid
token gets `401` with the metadata pointer; a token with the wrong `iss`/`aud`
gets `invalid_issuer`/`invalid_audience`; a token without the required scope
gets an explicit `insufficient_scope` tool error.

## Tests

```bash
uv run python -m pytest tests/mcps -q     # auth, protocol, scopes, read-only invariants
uv run python -m pytest tests/pipelines/test_mcp_client.py tests/pipelines/test_agent_graph_mcp.py -q
```

Design decisions and live acceptance evidence: `docs/rag/agent-graph.md` §4
(MCP transport) and §9.2 (deviation of §9.1).
