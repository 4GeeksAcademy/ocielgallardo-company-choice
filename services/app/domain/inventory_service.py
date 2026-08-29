"""Domain logic for HealthCore medical supply inventory."""

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, func, select

from services.app.core.ttl_cache import inventory_list_cache
from services.app.models.inventory import (
    MedicalSupply,
    SupplyConsumption,
    SupplyDelivery,
)
from services.app.schemas import (
    InventoryOrderResponse,
    MedicalSupplyCreate,
    MedicalSupplyResponse,
    SupplyConsumptionCreate,
    SupplyConsumptionResponse,
    SupplyDeliveryCreate,
    SupplyDeliveryResponse,
)

# Org-wide list keys (authenticated endpoints; response is not user-scoped).
CACHE_KEY_PRODUCTS = "inventory:products"
CACHE_KEY_ORDERS = "inventory:orders"
INVENTORY_LIST_TTL_SECONDS = 60


def _invalidate_inventory_lists() -> None:
    inventory_list_cache.invalidate(CACHE_KEY_PRODUCTS, CACHE_KEY_ORDERS)


def _stock_for_supply_id(session: Session, supply_id: int) -> int:
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


def _stocks_by_supply_id(session: Session) -> dict[int, int]:
    """Compute current_stock for all supplies in two aggregate queries (no N+1)."""
    delivery_rows = session.exec(
        select(
            SupplyDelivery.supply_id,
            func.coalesce(func.sum(SupplyDelivery.quantity), 0),
        ).group_by(SupplyDelivery.supply_id)
    ).all()
    consumption_rows = session.exec(
        select(
            SupplyConsumption.supply_id,
            func.coalesce(func.sum(SupplyConsumption.quantity), 0),
        ).group_by(SupplyConsumption.supply_id)
    ).all()

    delivered = {sid: int(total) for sid, total in delivery_rows}
    consumed = {sid: int(total) for sid, total in consumption_rows}
    supply_ids = set(delivered) | set(consumed)
    return {sid: delivered.get(sid, 0) - consumed.get(sid, 0) for sid in supply_ids}


def _to_supply_response(
    supply: MedicalSupply, current_stock: int
) -> MedicalSupplyResponse:
    return MedicalSupplyResponse(
        id=supply.id,
        name=supply.name,
        sku=supply.sku,
        category=supply.category,
        unit=supply.unit,
        country=supply.country,
        current_stock=current_stock,
    )


def list_supplies(session: Session) -> list[MedicalSupplyResponse]:
    cached = inventory_list_cache.get(CACHE_KEY_PRODUCTS)
    if cached is not None:
        return cached

    supplies = session.exec(select(MedicalSupply).order_by(MedicalSupply.id)).all()
    stocks = _stocks_by_supply_id(session)
    result = [
        _to_supply_response(s, stocks.get(s.id, 0))
        for s in supplies
        if s.id is not None
    ]
    inventory_list_cache.set(
        CACHE_KEY_PRODUCTS, result, INVENTORY_LIST_TTL_SECONDS
    )
    return result


def get_supply(session: Session, supply_id: int) -> MedicalSupplyResponse:
    supply = session.get(MedicalSupply, supply_id)
    if supply is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical supply {supply_id} not found",
        )
    return _to_supply_response(supply, _stock_for_supply_id(session, supply_id))


def create_supply(
    session: Session, payload: MedicalSupplyCreate
) -> MedicalSupplyResponse:
    existing = session.exec(
        select(MedicalSupply).where(MedicalSupply.sku == payload.sku)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"SKU '{payload.sku}' already exists",
        )
    supply = MedicalSupply(**payload.model_dump())
    session.add(supply)
    session.commit()
    session.refresh(supply)
    _invalidate_inventory_lists()
    return _to_supply_response(supply, 0)


def create_delivery(
    session: Session,
    payload: SupplyDeliveryCreate,
    user_uuid: str,
) -> SupplyDeliveryResponse:
    supply = session.get(MedicalSupply, payload.supply_id)
    if supply is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical supply {payload.supply_id} not found",
        )
    delivery = SupplyDelivery(
        **payload.model_dump(),
        user_uuid=user_uuid,
    )
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    _invalidate_inventory_lists()
    return SupplyDeliveryResponse(
        id=delivery.id,
        supply_id=delivery.supply_id,
        quantity=delivery.quantity,
        vendor_name=delivery.vendor_name,
        clinic_id=delivery.clinic_id,
        created_at=delivery.created_at,
        user_uuid=delivery.user_uuid,
    )


def create_consumption(
    session: Session,
    payload: SupplyConsumptionCreate,
    user_uuid: str,
) -> SupplyConsumptionResponse:
    supply = session.get(MedicalSupply, payload.supply_id)
    if supply is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical supply {payload.supply_id} not found",
        )
    available = _stock_for_supply_id(session, payload.supply_id)
    if payload.quantity > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock for supply '{supply.name}'. "
                f"Available: {available}, requested: {payload.quantity}."
            ),
        )
    consumption = SupplyConsumption(
        **payload.model_dump(),
        user_uuid=user_uuid,
    )
    session.add(consumption)
    session.commit()
    session.refresh(consumption)
    _invalidate_inventory_lists()
    return SupplyConsumptionResponse(
        id=consumption.id,
        supply_id=consumption.supply_id,
        quantity=consumption.quantity,
        consumption_type=consumption.consumption_type,
        clinic_id=consumption.clinic_id,
        created_at=consumption.created_at,
        user_uuid=consumption.user_uuid,
    )


def list_orders(session: Session) -> list[InventoryOrderResponse]:
    """List deliveries and consumptions with related supply data (eager-loaded)."""
    cached = inventory_list_cache.get(CACHE_KEY_ORDERS)
    if cached is not None:
        return cached

    deliveries = session.exec(
        select(SupplyDelivery)
        .options(selectinload(SupplyDelivery.supply))
        .order_by(col(SupplyDelivery.created_at).desc())
    ).all()
    consumptions = session.exec(
        select(SupplyConsumption)
        .options(selectinload(SupplyConsumption.supply))
        .order_by(col(SupplyConsumption.created_at).desc())
    ).all()

    orders: list[InventoryOrderResponse] = []
    for d in deliveries:
        supply = d.supply
        orders.append(
            InventoryOrderResponse(
                order_type="inbound",
                id=d.id,
                supply_id=d.supply_id,
                supply_name=supply.name if supply else "",
                supply_sku=supply.sku if supply else "",
                quantity=d.quantity,
                clinic_id=d.clinic_id,
                created_at=d.created_at,
                user_uuid=d.user_uuid,
                vendor_name=d.vendor_name,
            )
        )
    for c in consumptions:
        supply = c.supply
        orders.append(
            InventoryOrderResponse(
                order_type="outbound",
                id=c.id,
                supply_id=c.supply_id,
                supply_name=supply.name if supply else "",
                supply_sku=supply.sku if supply else "",
                quantity=c.quantity,
                clinic_id=c.clinic_id,
                created_at=c.created_at,
                user_uuid=c.user_uuid,
                consumption_type=c.consumption_type,
            )
        )
    orders.sort(key=lambda o: o.created_at, reverse=True)
    inventory_list_cache.set(CACHE_KEY_ORDERS, orders, INVENTORY_LIST_TTL_SECONDS)
    return orders
