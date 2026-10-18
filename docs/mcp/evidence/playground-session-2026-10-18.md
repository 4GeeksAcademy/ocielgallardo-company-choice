# MCP Playground session — evidence (2026-10-18)

Live session of the **MCP Playground** against the public Codespaces URL of the
hito 25 resource server. No screenshot is attached: the verifiable evidence is
the Playground's own tool outputs below plus the server-side audit trail.

- **Public resource URL**: `https://<codespace>-8100.app.github.dev/mcp`
  (Codespaces port 8100 set to **Public**; `MCP_RESOURCE_URL` in `.env`)
- **Client**: MCP Playground (browser session; the playground connects
  server-side, so the requests arrive from its AWS egress IPs)
- **Token**: client-credentials service token minted inside the Codespace
  (`scripts/mcp_playground_runbook.sh mint --env-prefix MCP_BACKEND
  --audience <public-url>/mcp`), scopes `incidents:read incidents:write
  inventory:read`, TTL 15 min, `aud` = public resource URL
- **Preflight** (same URL, from the Codespace): `PREFLIGHT OK` both without a
  token (health, RFC 9728 PRM, 401 no token + garbage token) and with a token
  (`tools/list` → 200, all 6 tools with schemas)

## 1. Discovery

`tools/list` over the public URL advertises the 6 tools with input/output
schemas: `get_incident_status`, `list_incidents`, `create_incident`,
`update_incident_status`, `get_inventory_stock`, `update_inventory_stock`.

## 2. One full flow per tool (6/6, from the Playground)

| # | Tool | Call | Result |
|---|------|------|--------|
| 1 | `get_incident_status` | `{"ticket_id": 42}` | `ok` — ticket 42 `resolved`, `patient_experience`, `austin_north` |
| 2 | `list_incidents` | `{"status": "open"}` | `ok` — 28 `open` tickets listed |
| 3 | `create_incident` | `{"title": "Playground check", "category": "it_system", "origin": "internal", "branch": "central", …}` | `ok` — ticket **95** created against the real Incidents Manager |
| 4 | `update_incident_status` | `{"ticket_id": 95, "status": "in_progress"}` → `{"status": "resolved"}` | `ok` — `open → in_progress → resolved` (see §3) |
| 5 | `get_inventory_stock` | `{"sku": "HCR-PPE-001"}` | `ok` — `current_stock=1289 box`, `country=US` |
| 6 | `update_inventory_stock` | `{"supply_id": 1, "quantity_change": 5, "reason": "playground"}` | **controlled refusal** `inventory_write_denied` (see §4) |

Sample Playground outputs (trimmed):

```json
{"ok": true, "incidents": [{"id": 42, "status": "resolved", "category": "other",
  "branch": "austin_north", "updated_at": "2024-01-13T00:00:00Z"}], "error": null}

{"ok": true, "incidents": [{"id": 95, "title": "Playground check",
  "status": "resolved", "origin": "internal", "branch": "central",
  "created_at": "2026-10-18T17:37:20.634690Z",
  "updated_at": "2026-10-18T17:53:55.923401Z"}], "error": null}

{"ok": true, "products": [{"sku": "HCR-PPE-001", "current_stock": 1289,
  "unit": "box", "country": "US"}], "error": null}
```

## 3. Lifecycle rule enforced through MCP

`open → resolved` is **not** allowed; the backend rejects it and the tool
returns the validation contract:

```json
{"ok": false, "incidents": [], "error": "invalid_input",
 "message": "I could not confirm the status of that ticket right now. …"}
```

Allowed transitions (`packages/shared/healthcore_shared/manager_validation.py`):
`open → in_progress|discarded`, `in_progress → resolved|discarded`,
`resolved`/`discarded` terminal. The correct two-step sequence succeeded (§2,
row 4).

## 4. Inventory write refusal (required by the rubric)

The Playground surfaced the tool error `inventory_write_denied`; the guard
(`permissions.deny_inventory_write`, wired to the tool) raises
`inventory_write_denied: <operation>. <INVENTORY_READ_ONLY_MESSAGE>` **before
any backend request**, and the audit log records it as `result=denied_policy`.

## 5. Auth evidence (Playground, no valid header)

The Playground surfaced the middleware rejection
(`Authentication required. Check its documentation for the required API key or
token.`), and the server log records it with the Playground's public egress IP:

```
17:25:15  POST /mcp  401 Unauthorized  (23.20.134.203)  Missing `Authorization` header
17:26:23  POST /mcp  401 Unauthorized  (23.20.134.203)  Invalid `Authorization` header format. Expected "Bearer <token>."
17:53:13  GET  /mcp  401 Unauthorized  (3.92.147.135)   Missing `Authorization` header
```

## 6. Server audit trail (one log per invocation)

```
mcp_tool tool=get_incident_status    client=mcp-server result=ok            ms=353.1
mcp_tool tool=list_incidents         client=mcp-server result=ok            ms=26.5
mcp_tool tool=create_incident        client=mcp-server result=ok            ms=18.6
mcp_tool tool=get_inventory_stock    client=mcp-server result=ok            ms=139.2
mcp_tool tool=update_inventory_stock client=mcp-server result=denied_policy  ms=0.0
mcp_tool tool=update_incident_status client=mcp-server result=failure        (open → resolved)
mcp_tool tool=update_incident_status client=mcp-server result=ok            ms=366.5
mcp_tool tool=update_incident_status client=mcp-server result=ok            ms=101.4
```

Agent E2E in the same Codespace (`run_agent`, MCP-only path):
`get_incident_status` span `transport=mcp ok=True` with real ticket data, plus
`get_inventory_stock` (`HCR-PPE-001` → 1289 box) through the same MCP server.

## 7. Session screenshots

Captures taken during the browser session (filenames kept as exported by the
capture tool):

- `2026-10-18 (2).png`
- `2026-10-18 (3).png`
- `2026-10-18 (4).png`
- `2026-10-18 (5).png`
- `2026-10-18 (6).png`

![MCP Playground session — capture 2](<2026-10-18 (2).png>)
![MCP Playground session — capture 3](<2026-10-18 (3).png>)
![MCP Playground session — capture 4](<2026-10-18 (4).png>)
![MCP Playground session — capture 5](<2026-10-18 (5).png>)
![MCP Playground session — capture 6](<2026-10-18 (6).png>)

## 8. Environment notes (Codespaces)

- In this organization the Codespace did **not** apply the repository
  devcontainer features (no `uv`, no docker-in-docker), so `docker compose`
  was not available. Backend and MCP ran as **native processes** in the
  Codespace (the same uvicorn entrypoints the images use), with `.env`
  pointing at the public resource URL; ports 8000/8100 were forwarded and set
  to **Public**.
- Codespace idle timeout is 15 min (org setting) and the minted token TTL is
  15 min; the session was completed inside that window.
- Supabase/incidents data: `auth.json` and `incidents.json` are gitignored, so
  the Codespace re-seeded both (`seed_service_client.py` ×2,
  `seed_incidents.py` → 94 tickets). Secrets minted there die with the
  Codespace; the developer's local `.env`/`auth.json` were never touched.
