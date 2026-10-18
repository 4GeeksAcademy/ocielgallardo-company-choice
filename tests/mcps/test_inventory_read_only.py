"""Invariants that keep inventory read-only and backend access narrow.

Four independent guarantees are asserted here, so a future change cannot quietly
open a write path:

1. **Endpoint allowlist** — every path the MCP server can reach is declared in
   ``backend_client.ENDPOINTS`` and inventory entries are ``GET``-only.
2. **No write helper** — the module exposes no inventory write function.
3. **Client behaviour** — non-2xx/timeout/transport answers map to the contract
   error taxonomy instead of raising into the tool layer.
4. **API policy** — inventory write routes in the API still depend on
   ``get_current_user`` (human-only), so service tokens are rejected there.
"""

from __future__ import annotations

import ast
from pathlib import Path

import httpx
import pytest

from incidents_inventory_mcp import backend_client

REPO_ROOT = Path(__file__).resolve().parents[2]

# Reviewed surface: the MCP server may only touch these API routes.
EXPECTED_ENDPOINTS = {
    "incidents_list": ("GET", "/api/incidents"),
    "incident_detail": ("GET", "/api/incidents/{ticket_id}"),
    "incident_create": ("POST", "/api/incidents"),
    "incident_status_update": ("PATCH", "/api/incidents/{ticket_id}/status"),
    "products_list": ("GET", "/inventory/products"),
    "product_detail": ("GET", "/inventory/products/{supply_id}"),
}


def test_endpoint_allowlist_is_exactly_the_reviewed_surface() -> None:
    assert backend_client.ENDPOINTS == EXPECTED_ENDPOINTS


def test_inventory_endpoints_are_get_only() -> None:
    inventory = {
        key: value
        for key, value in backend_client.ENDPOINTS.items()
        if key.startswith("product")
    }

    assert inventory, "inventory endpoints must stay declared (read-only by design)"
    for key, (method, path) in inventory.items():
        assert method == "GET", f"{key} must stay GET"
        assert path.startswith("/inventory/"), key


def test_no_inventory_write_helper_exists() -> None:
    public_names = [name for name in dir(backend_client) if not name.startswith("_")]

    assert not [
        name
        for name in public_names
        if "inventory" in name.lower() and any(verb in name for verb in ("create", "update", "set", "write", "delete"))
    ]
    source = Path(backend_client.__file__).read_text(encoding="utf-8")
    assert "PUT" not in source and "DELETE" not in source


def test_unknown_endpoint_key_is_refused_before_any_http_call(monkeypatch) -> None:
    import asyncio

    def _unexpected(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("no HTTP call may happen for an unknown endpoint")

    monkeypatch.setattr(httpx.AsyncClient, "request", _unexpected)

    with pytest.raises(backend_client.BackendError) as excinfo:
        asyncio.run(backend_client.request("inventory_restock"))

    assert excinfo.value.kind == "unavailable"
    assert "unknown endpoint" in excinfo.value.message


def _response(status: int) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        request=httpx.Request("GET", "http://127.0.0.1:8000/api/incidents/1"),
        json={"detail": "x"},
    )


@pytest.mark.parametrize(
    ("status", "kind"),
    [(400, "invalid_input"), (404, "not_found"), (422, "invalid_input"), (401, "auth"), (403, "auth"), (500, "unavailable")],
)
def test_status_codes_map_to_contract_kinds(status, kind) -> None:
    with pytest.raises(backend_client.BackendError) as excinfo:
        backend_client._raise_for_status(_response(status), "incident_detail")

    assert excinfo.value.kind == kind


def test_2xx_responses_do_not_raise() -> None:
    assert backend_client._raise_for_status(_response(200), "incident_detail") is None


def test_transport_failure_maps_to_unavailable(monkeypatch) -> None:
    import asyncio

    async def _boom(*args, **kwargs):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx.AsyncClient, "request", _boom)

    with pytest.raises(backend_client.BackendError) as excinfo:
        asyncio.run(backend_client.get_products())

    assert excinfo.value.kind == "unavailable"


def test_timeout_maps_to_timeout(monkeypatch) -> None:
    import asyncio

    async def _boom(*args, **kwargs):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(httpx.AsyncClient, "request", _boom)

    with pytest.raises(backend_client.BackendError) as excinfo:
        asyncio.run(backend_client.get_products())

    assert excinfo.value.kind == "timeout"


def test_backend_url_prefers_environment(monkeypatch) -> None:
    monkeypatch.setenv("MCP_BACKEND_URL", "http://backend:8000/")

    assert backend_client.backend_url() == "http://backend:8000"


def test_api_inventory_writes_stay_human_only() -> None:
    """Layer 5: service tokens cannot write inventory in the API either.

    Read from source with a static check so the guarantee holds without a
    database: every inventory write route must depend on ``get_current_user``.
    """
    source = (REPO_ROOT / "services" / "app" / "routers" / "inventory.py").read_text(
        encoding="utf-8"
    )
    module = ast.parse(source)

    write_routes: list[ast.FunctionDef] = []
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        decorators = [
            ast.unparse(decorator) for decorator in node.decorator_list
        ]
        if any(
            decorator.startswith("router.") and "get(" not in decorator
            for decorator in decorators
        ):
            write_routes.append(node)

    assert write_routes, "inventory write routes not found; check the static parser"
    for route in write_routes:
        text = ast.unparse(route)
        assert "get_current_user" in text, f"{route.name} must stay human-only"
        assert "require_scope" not in text, f"{route.name} must not accept service tokens"
