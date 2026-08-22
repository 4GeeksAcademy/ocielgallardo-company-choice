"""Idempotent seeder for HealthCore medical supply inventory (Supabase)."""

from sqlmodel import Session, select

from services.app.core.database import get_engine
from services.app.models.inventory import (
    MedicalSupply,
    SupplyConsumption,
    SupplyDelivery,
)

# Seed user_uuid values stand in for TinyDB user ids (string form).
SEED_USER_UUID = "1"

MEDICAL_SUPPLIES_SEED = [
    {
        "name": "Guantes de nitrilo (caja de 100)",
        "sku": "HCR-PPE-001",
        "category": "ppe",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Mascarilla quirúrgica (pack de 50)",
        "sku": "HCR-PPE-002",
        "category": "ppe",
        "unit": "pack",
        "country": "UK",
    },
    {
        "name": "Apósito adhesivo para heridas",
        "sku": "HCR-WND-001",
        "category": "wound_care",
        "unit": "box",
        "country": "US",
    },
    {
        "name": "Test rápido de estreptococo",
        "sku": "HCR-DIAG-001",
        "category": "diagnostics",
        "unit": "unit",
        "country": "US",
    },
    {
        "name": "Tiras reactivas glucemia (50)",
        "sku": "HCR-DIAG-002",
        "category": "diagnostics",
        "unit": "box",
        "country": "UK",
    },
    {
        "name": "Solución salina 0,9% 500ml",
        "sku": "HCR-MED-001",
        "category": "medications",
        "unit": "vial",
        "country": "US",
    },
]


def seed_inventory(session: Session | None = None) -> None:
    """Insert CONTEXT seed rows if the inventory tables are empty."""
    owns_session = session is None
    if owns_session:
        session = Session(get_engine())

    assert session is not None
    try:
        existing = session.exec(select(MedicalSupply)).first()
        if existing is not None:
            print("Inventory seed skipped: medical_supplies already has data.")
            return

        supplies: dict[str, MedicalSupply] = {}
        for row in MEDICAL_SUPPLIES_SEED:
            supply = MedicalSupply(**row)
            session.add(supply)
            supplies[row["sku"]] = supply
        session.flush()

        deliveries = [
            SupplyDelivery(
                supply_id=supplies["HCR-PPE-001"].id,
                quantity=40,
                vendor_name="MedLine Industries",
                clinic_id=1,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyDelivery(
                supply_id=supplies["HCR-PPE-001"].id,
                quantity=25,
                vendor_name="Bound Tree Medical",
                clinic_id=3,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyDelivery(
                supply_id=supplies["HCR-PPE-002"].id,
                quantity=30,
                vendor_name="Cardinal Health UK",
                clinic_id=10,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyDelivery(
                supply_id=supplies["HCR-DIAG-001"].id,
                quantity=50,
                vendor_name="MedLine Industries",
                clinic_id=2,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyDelivery(
                supply_id=supplies["HCR-WND-001"].id,
                quantity=20,
                vendor_name="Bound Tree Medical",
                clinic_id=5,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyDelivery(
                supply_id=supplies["HCR-DIAG-002"].id,
                quantity=15,
                vendor_name="Cardinal Health UK",
                clinic_id=12,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyDelivery(
                supply_id=supplies["HCR-MED-001"].id,
                quantity=18,
                vendor_name="MedLine Industries",
                clinic_id=1,
                user_uuid=SEED_USER_UUID,
            ),
        ]
        for delivery in deliveries:
            session.add(delivery)

        consumptions = [
            SupplyConsumption(
                supply_id=supplies["HCR-PPE-001"].id,
                quantity=10,
                consumption_type="clinical_use",
                clinic_id=1,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyConsumption(
                supply_id=supplies["HCR-PPE-002"].id,
                quantity=5,
                consumption_type="expiry_waste",
                clinic_id=10,
                user_uuid=SEED_USER_UUID,
            ),
            SupplyConsumption(
                supply_id=supplies["HCR-DIAG-001"].id,
                quantity=8,
                consumption_type="clinical_use",
                clinic_id=2,
                user_uuid=SEED_USER_UUID,
            ),
        ]
        for consumption in consumptions:
            session.add(consumption)

        session.commit()
        print(
            "Inventory seed completed: "
            f"{len(MEDICAL_SUPPLIES_SEED)} supplies, "
            f"{len(deliveries)} deliveries, "
            f"{len(consumptions)} consumptions."
        )
    finally:
        if owns_session:
            session.close()


def run_inventory_seed() -> None:
    from services.app.core.database import init_inventory_db

    init_inventory_db()
    seed_inventory()


if __name__ == "__main__":
    run_inventory_seed()
