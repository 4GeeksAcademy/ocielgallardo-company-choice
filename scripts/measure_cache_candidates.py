"""Measure row counts and domain/HTTP latency for caching candidate endpoints."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, func, select  # noqa: E402

from services.app.core.database import (  # noqa: E402
    get_engine,
    incidents_table,
    init_inventory_db,
    is_inventory_db_configured,
    suppliers_table,
)
from services.app.domain.incident_manager_service import get_incident_summary  # noqa: E402
from services.app.domain.inventory_service import list_orders, list_supplies  # noqa: E402
from services.app.domain.supplier_service import list_suppliers  # noqa: E402
from services.app.models.inventory import (  # noqa: E402
    MedicalSupply,
    SupplyConsumption,
    SupplyDelivery,
)

DEFAULT_ITERATIONS = 10
DEFAULT_API_BASE = "http://127.0.0.1:8000"


def _percentile_ms(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = max(0, min(len(ordered) - 1, int(round(p * (len(ordered) - 1)))))
    return ordered[idx]


def _summarize(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"min_ms": 0.0, "p50_ms": 0.0, "max_ms": 0.0}
    return {
        "min_ms": round(min(samples), 2),
        "p50_ms": round(statistics.median(samples), 2),
        "max_ms": round(max(samples), 2),
    }


def _time_call(fn, iterations: int) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return _summarize(samples)


def _inventory_counts(session: Session) -> dict[str, int]:
    return {
        "medical_supplies": int(
            session.exec(select(func.count()).select_from(MedicalSupply)).one()
        ),
        "supply_deliveries": int(
            session.exec(select(func.count()).select_from(SupplyDelivery)).one()
        ),
        "supply_consumptions": int(
            session.exec(select(func.count()).select_from(SupplyConsumption)).one()
        ),
    }


def measure_domain(iterations: int) -> dict:
    if not is_inventory_db_configured():
        raise SystemExit(
            "Database not configured. Set DATABASE_URL or SUPABASE_DB_* in .env"
        )

    init_inventory_db()
    with Session(get_engine()) as session:
        counts = _inventory_counts(session)

        def run_list_supplies() -> None:
            list_supplies(session)

        def run_list_orders() -> None:
            list_orders(session)

        inventory = {
            "list_supplies_ms": _time_call(run_list_supplies, iterations),
            "list_orders_ms": _time_call(run_list_orders, iterations),
        }

    return {
        "mode": "domain",
        "iterations": iterations,
        "row_counts": {
            **counts,
            "incidents": len(incidents_table),
            "suppliers": len(suppliers_table),
        },
        "latency_ms": {
            "inventory_products": inventory["list_supplies_ms"],
            "inventory_orders": inventory["list_orders_ms"],
            "incidents_summary": _time_call(get_incident_summary, iterations),
            "suppliers_list": _time_call(list_suppliers, iterations),
        },
    }


def _http_request(
    method: str,
    url: str,
    token: str | None = None,
    body: dict | None = None,
) -> tuple[int, float]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.read()
    duration_ms = (time.perf_counter() - start) * 1000
    return status, duration_ms


def _login(base_url: str) -> str:
    username = os.getenv("BENCHMARK_USERNAME")
    password = os.getenv("BENCHMARK_PASSWORD")
    if not username or not password:
        raise SystemExit(
            "HTTP mode requires BENCHMARK_USERNAME and BENCHMARK_PASSWORD in .env"
        )

    req = urllib.request.Request(
        f"{base_url}/auth/login",
        data=json.dumps({"username": username, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            raise SystemExit(f"Login failed with status {resp.status}")
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["access_token"]


def _time_http_get(base_url: str, path: str, token: str, iterations: int) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(iterations):
        status, duration_ms = _http_request("GET", f"{base_url}{path}", token=token)
        if status != 200:
            raise SystemExit(f"GET {path} failed with status {status}")
        samples.append(duration_ms)
    return _summarize(samples)


def measure_http(base_url: str, iterations: int) -> dict:
    token = _login(base_url)
    domain = measure_domain(iterations=1)

    return {
        "mode": "http",
        "api_base": base_url,
        "iterations": iterations,
        "row_counts": domain["row_counts"],
        "latency_ms": {
            "inventory_products": _time_http_get(
                base_url, "/inventory/products", token, iterations
            ),
            "inventory_orders": _time_http_get(
                base_url, "/inventory/orders", token, iterations
            ),
            "incidents_summary": _time_http_get(
                base_url, "/api/incidents/summary", token, iterations
            ),
            "suppliers_list": _time_http_get(
                base_url, "/suppliers", token, iterations
            ),
        },
    }


def _print_report(report: dict) -> None:
    print(f"Mode: {report['mode']} | iterations: {report['iterations']}")
    print("\nRow counts:")
    for key, value in report["row_counts"].items():
        print(f"  {key}: {value}")

    print("\nLatency (ms):")
    for key, stats in report["latency_ms"].items():
        print(
            f"  {key}: min={stats['min_ms']} p50={stats['p50_ms']} max={stats['max_ms']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure caching candidate endpoints")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Measure via HTTP against a running API (requires login env vars)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_API_BASE,
        help=f"API base URL for --http mode (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Iterations per endpoint (default: {DEFAULT_ITERATIONS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of human-readable output",
    )
    args = parser.parse_args()

    report = (
        measure_http(args.base_url, args.iterations)
        if args.http
        else measure_domain(args.iterations)
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)


if __name__ == "__main__":
    main()
