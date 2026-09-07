"""Pydantic request/response schemas for HealthCore inventory API.

Kept separate from SQLModel ORM tables in ``models.inventory``.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SupplyCategory = Literal[
    "ppe",
    "wound_care",
    "diagnostics",
    "medications",
    "consumables",
]
SupplyUnit = Literal["box", "unit", "pack", "vial"]
SupplyCountry = Literal["US", "UK"]
ConsumptionType = Literal["clinical_use", "expiry_waste"]


class MedicalSupplyCreate(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    category: SupplyCategory
    unit: SupplyUnit
    country: SupplyCountry


class MedicalSupplyResponse(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    unit: str
    country: str
    current_stock: int


class SupplyDeliveryCreate(BaseModel):
    supply_id: int
    quantity: int = Field(gt=0)
    vendor_name: str = Field(min_length=1)
    clinic_id: int = Field(ge=1, le=12)


class SupplyDeliveryResponse(BaseModel):
    id: int
    supply_id: int
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class SupplyConsumptionCreate(BaseModel):
    supply_id: int
    quantity: int = Field(gt=0)
    consumption_type: ConsumptionType
    clinic_id: int = Field(ge=1, le=12)


class SupplyConsumptionResponse(BaseModel):
    id: int
    supply_id: int
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime
    user_uuid: str


class InventoryOrderResponse(BaseModel):
    """Full unified order row (internal / write-adjacent projections)."""

    order_type: Literal["inbound", "outbound"]
    id: int
    supply_id: int
    supply_name: str
    supply_sku: str
    quantity: int
    clinic_id: int
    created_at: datetime
    user_uuid: str
    vendor_name: str | None = None
    consumption_type: str | None = None


class InventoryOrderListItem(BaseModel):
    """Lean history row for GET /inventory/orders (backoffice table columns)."""

    order_type: Literal["inbound", "outbound"]
    id: int
    supply_name: str
    quantity: int
    created_at: datetime
    user_uuid: str

class TelemetryEvent(BaseModel):
    """Standard event envelope from the HealthCore telemetry plan (Phase 1)."""

    eventId: str
    timestamp: datetime
    sessionId: str | None
    userId: str
    event_type: str
    schemaVersion: str
    requestId: str | None
    properties: dict[str, object]


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent]


class TelemetryIngestResponse(BaseModel):
    received: int