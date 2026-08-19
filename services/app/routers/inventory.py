"""Inventory API router — all routes under /inventory (authenticated)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from services.app.core.database import get_db
from services.app.core.deps import get_current_user
from services.app.domain import inventory_service
from services.app.models.user import UserPublic
from services.app.schemas import (
    InventoryOrderResponse,
    MedicalSupplyCreate,
    MedicalSupplyResponse,
    SupplyConsumptionCreate,
    SupplyConsumptionResponse,
    SupplyDeliveryCreate,
    SupplyDeliveryResponse,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _user_uuid(user: UserPublic) -> str:
    """TinyDB user id as string (no user table in Supabase)."""
    return str(user.id)


@router.get("/products", response_model=list[MedicalSupplyResponse])
def list_products(
    _: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[MedicalSupplyResponse]:
    return inventory_service.list_supplies(session)


@router.post("/products", response_model=MedicalSupplyResponse, status_code=201)
def create_product(
    payload: MedicalSupplyCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> MedicalSupplyResponse:
    _ = current_user
    return inventory_service.create_supply(session, payload)


@router.get("/products/{supply_id}", response_model=MedicalSupplyResponse)
def get_product(
    supply_id: int,
    _: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> MedicalSupplyResponse:
    return inventory_service.get_supply(session, supply_id)


@router.post(
    "/orders/inbound",
    response_model=SupplyDeliveryResponse,
    status_code=201,
)
def create_inbound_order(
    payload: SupplyDeliveryCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SupplyDeliveryResponse:
    return inventory_service.create_delivery(
        session, payload, _user_uuid(current_user)
    )


@router.post(
    "/orders/outbound",
    response_model=SupplyConsumptionResponse,
    status_code=201,
)
def create_outbound_order(
    payload: SupplyConsumptionCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SupplyConsumptionResponse:
    return inventory_service.create_consumption(
        session, payload, _user_uuid(current_user)
    )


@router.get("/orders", response_model=list[InventoryOrderResponse])
def list_orders(
    _: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[InventoryOrderResponse]:
    return inventory_service.list_orders(session)
