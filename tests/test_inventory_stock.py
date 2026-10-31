"""Stock can never go below zero when recording a consumption (outbound order).

Offline: in-memory SQLite + dependency overrides, no Supabase/network.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("SECRET_KEY", "inventory-stock-test-secret")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine, func, select  # noqa: E402

from services.app.core.database import get_db  # noqa: E402
from services.app.core.deps import get_current_user  # noqa: E402
from services.app.core.ttl_cache import inventory_list_cache  # noqa: E402
from services.app.domain import inventory_service  # noqa: E402
from services.app.domain.inventory_service import (  # noqa: E402
    CACHE_KEY_ORDERS,
    CACHE_KEY_PRODUCTS,
)
from services.app.models.inventory import (  # noqa: E402
    MedicalSupply,
    SupplyConsumption,
    SupplyDelivery,
)
from services.app.models.user import UserPublic, UserRole  # noqa: E402
from services.app.routers.inventory import router as inventory_router  # noqa: E402

_USER = UserPublic(
    id=7,
    email="stock.tester@healthcore.example",
    is_active=True,
    role=UserRole.USER,
    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)


@pytest.fixture()
def ctx():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            MedicalSupply.__table__,
            SupplyDelivery.__table__,
            SupplyConsumption.__table__,
        ],
    )
    with Session(engine) as session:
        supply = MedicalSupply(
            name="Nitrile gloves",
            sku="TEST-PPE-001",
            category="ppe",
            unit="box",
            country="US",
        )
        session.add(supply)
        session.commit()
        session.refresh(supply)
        session.add(
            SupplyDelivery(
                supply_id=supply.id,
                quantity=10,
                vendor_name="MedLine Industries",
                clinic_id=1,
                user_uuid="7",
            )
        )
        session.commit()
        supply_id = supply.id

    def _get_db():
        with Session(engine) as session:
            yield session

    app = FastAPI()
    app.include_router(inventory_router)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: _USER
    inventory_list_cache.invalidate(CACHE_KEY_PRODUCTS, CACHE_KEY_ORDERS)
    with TestClient(app) as client:
        yield client, engine, supply_id
    inventory_list_cache.invalidate(CACHE_KEY_PRODUCTS, CACHE_KEY_ORDERS)
    engine.dispose()


def _consume(client: TestClient, supply_id: int, quantity: int):
    return client.post(
        "/inventory/orders/outbound",
        json={
            "supply_id": supply_id,
            "quantity": quantity,
            "consumption_type": "clinical_use",
            "clinic_id": 1,
        },
    )


def _stock(engine, supply_id: int) -> int:
    with Session(engine) as session:
        delivered = session.exec(
            select(func.coalesce(func.sum(SupplyDelivery.quantity), 0)).where(
                SupplyDelivery.supply_id == supply_id
            )
        ).one()
        consumed = session.exec(
            select(func.coalesce(func.sum(SupplyConsumption.quantity), 0)).where(
                SupplyConsumption.supply_id == supply_id
            )
        ).one()
    return int(delivered) - int(consumed)


def _consumption_count(engine) -> int:
    with Session(engine) as session:
        return int(
            session.exec(select(func.count()).select_from(SupplyConsumption)).one()
        )


def test_consumption_greater_than_stock_is_rejected_without_changing_stock(ctx):
    client, engine, supply_id = ctx

    response = _consume(client, supply_id, 11)

    assert response.status_code == 409
    assert "Insufficient stock" in response.json()["detail"]
    assert "Available: 10" in response.json()["detail"]
    assert _stock(engine, supply_id) == 10
    assert _consumption_count(engine) == 0


def test_consumption_equal_to_stock_leaves_zero(ctx):
    client, engine, supply_id = ctx

    response = _consume(client, supply_id, 10)

    assert response.status_code == 201
    assert _stock(engine, supply_id) == 0
    with Session(engine) as session:
        assert inventory_service.get_supply(session, supply_id).current_stock == 0


def test_any_consumption_at_zero_stock_is_rejected(ctx):
    client, engine, supply_id = ctx

    assert _consume(client, supply_id, 10).status_code == 201
    response = _consume(client, supply_id, 1)

    assert response.status_code == 409
    assert _stock(engine, supply_id) == 0
    assert _consumption_count(engine) == 1


def test_unknown_supply_returns_404(ctx):
    client, _, _ = ctx

    assert _consume(client, 999_999, 1).status_code == 404
