"""SQLModel ORM tables for HealthCore medical supply inventory (Supabase)."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class MedicalSupply(SQLModel, table=True):
    __tablename__ = "medical_supplies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(index=True, unique=True)
    category: str
    unit: str
    country: str

    deliveries: list["SupplyDelivery"] = Relationship(back_populates="supply")
    consumptions: list["SupplyConsumption"] = Relationship(back_populates="supply")


class SupplyDelivery(SQLModel, table=True):
    __tablename__ = "supply_deliveries"

    id: Optional[int] = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supplies.id", index=True)
    quantity: int
    vendor_name: str
    clinic_id: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_uuid: str

    supply: Optional[MedicalSupply] = Relationship(back_populates="deliveries")


class SupplyConsumption(SQLModel, table=True):
    __tablename__ = "supply_consumptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    supply_id: int = Field(foreign_key="medical_supplies.id", index=True)
    quantity: int
    consumption_type: str
    clinic_id: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    user_uuid: str

    supply: Optional[MedicalSupply] = Relationship(back_populates="consumptions")
