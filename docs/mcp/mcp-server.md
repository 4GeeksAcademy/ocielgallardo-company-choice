# MCP server — HealthCore incidents + inventory (hito 25)

Cross-cutting design and validation notes for the standalone MCP server that
exposes the company's incident-management and inventory tools to any
OAuth-authorized MCP client. Package-level reference (tools, scopes, error
catalog, configuration, run, connect): `mcps/incidents-inventory-mcp/README.md`.
Playground walkthrough: [`playground-codespaces.md`](./playground-codespaces.md).

## 1. What it is and why

The agent already knew how to call the Incidents Manager, but those calls were
hardcoded inside its graph, so every future integration would have reimplemented
them. The MCP server turns them into a reusable, authenticated service:

```
MCP client (agent, Playground, partner)
        │  Streamable HTTP + Authorization: Bearer <service JWT>
        ▼
mcps/incidents-inventory-mcp  (compose service `mcp`, :8100)
        │  OAuth resource server (mcpauth) → 401/403 or AUTH_CONTEXT
        │  own service identity (svc:mcp-server)
        ▼
HealthCore API (:8000)  — Incidents Manager + inventory endpoints
```

No new data path and no new business rules: the server fronts the existing API.

## 2. Design decisions (the four the brief leaves open)

### 2.1 Transport: Streamable HTTP, not stdio

The server must be consumed by **multiple remote clients** (the agent plus
Playground/other teams), so it is **Streamable HTTP** (official SDK's
`streamable_http` on `:8100`), not stdio. Consequence for auth: an HTTP
transport has a real network boundary, so it is protected by a **Bearer token**
and advertises **RFC 9728** protected-resource metadata; stdio would have relied
on process locality instead. `stateless_http=True` keeps it horizontally
scalable behind the Codespaces port forward.

### 2.2 Permissions: least privilege, enforced per tool

Authorization is **per tool**, not transport-wide: the same connection can read
and still be denied a write.

| Tool | Scope |
|------|-------|
| `get_incident_status`, `list_incidents` | `incidents:read` |
| `create_incident`, `update_incident_status` | `incidents:write` |
| `get_inventory_stock` | `inventory:read` |
| `update_inventory_stock` | none — always refuses |

Inventory is read-only **by design**, in layers: a refusal tool, the scope gate,
a GET-only endpoint allowlist (`backend_client`), no write helpers in the server
module, and human-only write routes in the API. A write attempt is rejected
explicitly (`inventory_write_denied`), never silently omitted. The server also
re-authenticates to the API with **its own** identity (`svc:mcp-server`), so an
MCP caller can never write with a scope it was not granted.

### 2.3 Discovery: enough for a client with no human context

`tools/list` advertises each tool's **name, description and JSON schema** for
input and output (`structured_output=True` → `inputSchema` + `outputSchema`), so
an external agent can understand what the server can and cannot do without
reading the source. `/.well-known/oauth-protected-resource/mcp` advertises the
resource identity, scopes and authorization server, so a client can discover how
to authenticate.

### 2.4 Agent migration: one path, no fallback

The graph's `lookup_incident` / `lookup_inventory` nodes now go through
`data/pipelines/mcp_client.py` only. The previous direct-`httpx` tools were
removed; a failed hop surfaces an honest `unavailable` contract instead of a
second route. Routing between RAG and tools is unchanged. See
[`../rag/agent-graph.md`](../rag/agent-graph.md) §4 and §9.2.

## 3. Authentication and authorization

- **Resource server via MCP Auth (`mcpauth`)** — no FastMCP auth helpers.
- **Token validation**: startup fetches the issuer's discovery document and
  verifies each token against that issuer's **RS256 JWKS**; `iss` must equal the
  issuer and `aud` must equal `MCP_RESOURCE_URL` (RFC 8707). Only client-credentials
  service tokens validate; human session tokens (HS256) cannot. No shared
  symmetric secret in this process.
- **Scope gate**: `permissions.require_scopes` reads the verified identity from a
  context variable, fail-closed when absent.
- **JWKS reachability**: discovery advertises the public issuer with
  `jwks_uri=http://localhost:8000/...`, which the `mcp` container cannot resolve.
  `MCP_AUTH_JWKS_URI` overrides **only** the JWKS URL (compose:
  `http://backend:8000/.well-known/jwks.json`), so `iss` stays the public issuer
  while signature verification works in-network.

## 4. Error catalog (distinct codes)

Transport level (before any tool runs; JSON body **and** `WWW-Authenticate`
carry the code + `resource_metadata`):

| Code | HTTP | Meaning |
|------|------|---------|
| `missing_auth_header` | 401 | No `Authorization` header |
| `invalid_auth_header_format` | 401 | Header is not `Bearer <token>` |
| `missing_bearer_token` | 401 | `Bearer` with an empty token |
| `invalid_token` | 401 | Bad signature / expired / malformed / not verifiable via JWKS |
| `invalid_issuer` | 401 | `iss` is not the configured authorization server |
| `invalid_audience` | 401 | `aud` is not this resource |

Tool level (valid token; authorization or contract outcome):

| Marker | Surface | Meaning |
|--------|---------|---------|
| `insufficient_scope: missing <scope>` | tool error (`isError`) | Token lacks the scope the tool requires |
| `inventory_write_denied` | tool error (`isError`) | Explicit read-only refusal |
| `not_found` / `timeout` / `unavailable` / `invalid_input` / `auth` | contract payload (`ok: false`) | Backend outcome reported as data |
| validation error (Pydantic) | tool error (`isError`) | Arguments do not satisfy the tool schema |
| `Unknown tool` | tool error | Tool name not registered |

**Why no HTTP 403 for scope denial.** MCP Auth emits `403
missing_required_scopes` only for transport-wide `required_scopes`. This server
deliberately does not set them: a read-only client must still be able to connect
and list tools, and MCP defines tool-level authorization failures as **tool
results**. Denials therefore return a successful RPC with `isError: true` and a
distinct marker, which is what an external MCP client sees.

## 5. Traceability (one log per tool invocation)

Every invocation logs `tool=` `client=` `result=` `ms=`, including denials:

```bash
docker compose logs mcp | grep mcp_tool
# mcp_tool tool=get_inventory_stock client=langgraph-agent result=ok ms=343.8
# mcp_tool tool=update_inventory_stock client=langgraph-agent result=denied_policy ms=0.0
# mcp_tool tool=create_incident client=langgraph-agent result=denied_scope ms=1.0
```

`result` ∈ `ok | denied_scope | denied_policy | error`.

## 6. Validation evidence (live stack, 2026-10-18)

Host-side `curl`/agent against `http://localhost:8100/mcp`, with a
client-credentials service token (`scripts/mint_service_token.py`):

| Rubric item | Evidence |
|-------------|----------|
| No valid token cannot list/invoke | `401 missing_auth_header` (no header), `401 invalid_token` (garbage), `401 invalid_audience` (wrong `aud`) — each with `WWW-Authenticate … resource_metadata=…` |
| Tools discoverable via discovery | `tools/list` → 200, 6 tools with descriptions and input/output schemas |
| Ticket tool against the real Incidents Manager | `get_incident_status {ticket_id:1}` → live record; `run_agent("What is the status of ticket 1?")` → `transport: "mcp"` |
| Inventory read + explicit write refusal | `get_inventory_stock {sku:"HCR-PPE-001"}` → stock; `update_inventory_stock` → `isError` `inventory_write_denied` |
| Distinct auth/authz/validation codes | 401 set above; `insufficient_scope: missing incidents:write`; Pydantic validation tool error |
| One log per invocation | `mcp_tool tool= client= result= ms=` (§5) |
| Agent uses MCP only | `run_agent` spans record `transport: "mcp"`; no direct-`httpx` tool route remains |
| Playground with public URL | MCP Playground session over the public Codespaces URL: 6/6 tool flows, `inventory_write_denied`, lifecycle rejection (`invalid_input`), `401` without/with malformed header — evidence in `docs/mcp/evidence/playground-session-2026-10-18.md` |

`scripts/mcp_playground_runbook.sh preflight` automates the first four rows.

### 6.1 MCP Playground session (public URL, 2026-10-18)

Human session from the **MCP Playground** against the Codespaces-forwarded
public URL (server-side connections from the Playground's egress IPs):

- Discovery: all 6 tools with schemas; one full flow per tool (`get_incident_status`
  on ticket 42, `list_incidents open`, `create_incident` → ticket **95**,
  `update_incident_status` `open → in_progress → resolved`, `get_inventory_stock`
  HCR-PPE-001 → 1289, `update_inventory_stock` → controlled refusal).
- Lifecycle: `open → resolved` is rejected (`invalid_input`); the two-step path
  is the only accepted one.
- Auth: without/with a malformed `Authorization` header the Playground shows the
  rejection and the server logs `401` with the Playground IPs; every invocation
  is audited (`mcp_tool … client=mcp-server result=ok|denied_policy`).

Full raw evidence: `docs/mcp/evidence/playground-session-2026-10-18.md`.

## 7. Known limits / TODOs

- Local endpoint-security software can rewrite plain-HTTP `/mcp` responses;
  see the caveat in `playground-codespaces.md`.
- Client-credentials only: no authorization-code flow or RFC 7523 client
  authentication yet.
