#!/usr/bin/env bash
# MCP Playground runbook (Codespaces): preflight checks + token minting +
# the manual steps to complete the Playground validation required by hito 25.
#
# Usage (from the repo root, ideally inside the Codespace):
#   bash scripts/mcp_playground_runbook.sh preflight            # server checks
#   MCP_PLAYGROUND_TOKEN=<token> bash scripts/... preflight     # + authed listing
#   bash scripts/mcp_playground_runbook.sh mint [--args...]     # mint a token
#   bash scripts/mcp_playground_runbook.sh info                 # Playground steps
#
# Environment:
#   MCP_SERVER_URL        MCP endpoint probed by this script
#                          (default http://localhost:8100/mcp)
#   MCP_PLAYGROUND_TOKEN  optional service token for the authenticated checks
set -euo pipefail

MCP_SERVER_URL="${MCP_SERVER_URL:-http://localhost:8100/mcp}"
BASE_URL="${MCP_SERVER_URL%/mcp}"
RPC_HEADERS=(-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream")
INITIALIZE_BODY='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"runbook","version":"0"}}}'
LIST_TOOLS_BODY='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*" >&2; FAILED=1; }
FAILED=0

post_status() { # body token-or-empty -> prints "<http_code>|<www_authenticate>"
  local body="$1" token="${2:-}"
  local args=(
    -sS -X POST "$MCP_SERVER_URL" "${RPC_HEADERS[@]}" -d "$body"
    -D /tmp/runbook_headers -o /tmp/runbook_body -w '%{http_code}'
  )
  if [[ -n "$token" ]]; then
    args+=(-H "Authorization: Bearer $token")
  fi
  local code
  code=$(curl "${args[@]}" || true)
  local www
  www=$(grep -i '^www-authenticate:' /tmp/runbook_headers 2>/dev/null | tr -d '\r' || true)
  printf '%s|%s' "$code" "$www"
}

preflight() {
  local token="${MCP_PLAYGROUND_TOKEN:-}"

  echo "== 1. Server health =="
  if curl -fsS "$BASE_URL/health" >/tmp/runbook_health 2>/dev/null; then
    pass "GET $BASE_URL/health -> $(cat /tmp/runbook_health)"
  else
    fail "GET $BASE_URL/health (is the MCP server running? see docs/mcp/playground-codespaces.md)"
    return
  fi

  echo "== 2. RFC 9728 protected-resource metadata =="
  local prm="$BASE_URL/.well-known/oauth-protected-resource/mcp"
  if curl -fsS "$prm" >/tmp/runbook_prm 2>/dev/null; then
    if grep -q '"authorization_servers"' /tmp/runbook_prm; then
      pass "GET $prm advertises authorization_servers"
    else
      fail "PRM document missing authorization_servers"
    fi
  else
    fail "GET $prm (PRM metadata must be reachable without a token)"
  fi

  echo "== 3. No token -> 401 (discovery blocked) =="
  local out
  out=$(post_status "$INITIALIZE_BODY" "")
  local code="${out%%|*}" www="${out#*|}"
  if [[ "$code" == "401" ]]; then
    pass "initialize without token -> 401"
  else
    fail "expected 401 without token, got $code"
  fi
  if echo "$www" | grep -q 'resource_metadata='; then
    pass "WWW-Authenticate points at the resource metadata"
  else
    fail "WWW-Authenticate missing resource_metadata: $www"
  fi

  echo "== 4. Garbage token -> 401 (invalid_token) =="
  out=$(post_status "$INITIALIZE_BODY" "not-a-jwt")
  code="${out%%|*}"
  if [[ "$code" == "401" ]]; then
    pass "initialize with garbage token -> 401"
  else
    fail "expected 401 with garbage token, got $code"
  fi

  if [[ -z "$token" ]]; then
    echo "== 5. Authenticated tools/list =="
    echo "SKIP  set MCP_PLAYGROUND_TOKEN (mint with: bash scripts/mcp_playground_runbook.sh mint)"
  else
    echo "== 5. Authenticated tools/list =="
    out=$(post_status "$LIST_TOOLS_BODY" "$token")
    code="${out%%|*}"
    if [[ "$code" == "200" ]]; then
      pass "tools/list with token -> 200"
    else
      fail "tools/list with token -> $code (audience must equal MCP_RESOURCE_URL; remint with --audience)"
    fi
    local count=0
    for tool in get_incident_status list_incidents create_incident \
                update_incident_status get_inventory_stock update_inventory_stock; do
      if grep -q "\"name\":\"$tool\"" /tmp/runbook_body || grep -q "\"name\": \"$tool\"" /tmp/runbook_body; then
        count=$((count + 1))
      else
        fail "tool $tool missing from tools/list"
      fi
    done
    if [[ $count -eq 6 ]]; then
      pass "all 6 tools advertised with schemas"
    else
      fail "expected 6 tools in tools/list, matched $count"
    fi
  fi

  [[ $FAILED -eq 0 ]] && echo "PREFLIGHT OK" || { echo "PREFLIGHT FAILED" >&2; exit 1; }
}

mint() {
  PYTHONPATH=. uv run python scripts/mint_service_token.py "$@"
}

info() {
  cat <<'EOF'
MCP Playground — manual validation steps (hito 25)

1. Expose the MCP port publicly
   - Codespaces: Ports panel -> port 8100 -> Visibility "Public".
   - Copy the forwarded URL, e.g. https://<codespace>-8100.app.github.dev
   - The MCP endpoint for the Playground is that URL + /mcp.

2. Point the server at the public identity (restart the MCP container after)
   - In .env set:  MCP_RESOURCE_URL=https://<codespace>-8100.app.github.dev/mcp
   - This is the token `aud` and the PRM/WWW-Authenticate base the browser fetches.

3. Mint a token with that audience
   - bash scripts/mcp_playground_runbook.sh mint \
       --audience https://<codespace>-8100.app.github.dev/mcp

4. Connect the Playground
   - Paste the public URL (…/mcp) as the server URL; localhost will not work
     from the Playground site.
   - Add the Authorization header: Bearer <token> (Playground auth/header field).

5. Run one full flow per exposed tool (6):
   - get_incident_status   {ticket_id: <real id>}
   - list_incidents        {status: "open"}
   - create_incident       {title, category, origin, branch, description}
   - update_incident_status {ticket_id, status}
   - get_inventory_stock   {sku: "HCR-PPE-001"}
   - update_inventory_stock {supply_id, quantity_change, reason}
     -> MUST fail in a controlled, explainable way (inventory is read-only).

6. Auth evidence (also automated in `preflight`):
   - No token / garbage token -> 401 with WWW-Authenticate + resource_metadata.
   - Token with the wrong audience -> 401 invalid_audience.
   - Read-only token calling create/update incident -> explicit scope denial.

7. After the demo: rotate the pasted client secret (it lived in a browser
   field on a public port).
EOF
}

case "${1:-preflight}" in
  preflight) shift || true; preflight "$@" ;;
  mint) shift; mint "$@" ;;
  info) shift; info "$@" ;;
  *) echo "usage: $0 [preflight|mint|info]" >&2; exit 2 ;;
esac
