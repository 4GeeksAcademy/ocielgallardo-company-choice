"""Append realistic inventory volume for caching benchmark (Supabase).

Idempotent: skips when supply_deliveries already exceeds MIN_DELIVERIES threshold.
Does not modify services/app/core/inventory_seed.py (CONTEXT 6-product seed).
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, func, select  # noqa: E402

from services.app.core.database import (  # noqa: E402
    get_engine,
    init_inventory_db,
    is_inventory_db_configured,
)
from services.app.models.inventory import (  # noqa: E402
    MedicalSupply,
    SupplyConsumption,
    SupplyDelivery,
)

MIN_DELIVERIES = 1000
EXTRA_PRODUCTS = 200
TARGET_DELIVERIES = 4000
TARGET_CONSUMPTIONS = 3500
BATCH_SIZE = 500
SEED_USER_UUID = "1"

CATEGORIES = ("ppe", "diagnostics", "wound_care", "medications")
UNITS = {
    "ppe": "box",
    "diagnostics": "unit",
    "wound_care": "box",
    "medications": "vial",
}
VENDORS = (
    "MedLine Industries",
    "Bound Tree Medical",
    "Cardinal Health UK",
    "Henry Schein",
    "McKesson Medical",
)
CONSUMPTION_TYPES = ("clinical_use", "expiry_waste", "transfer", "emergency_use")


def _count(session: Session, model) -> int:
    return int(session.exec(select(func.count()).select_from(model)).one())


def _random_created_at(rng: random.Random) -> datetime:
    days_ago = rng.randint(0, 540)
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return base.replace(
        hour=rng.randint(7, 18),
        minute=rng.randint(0, 59),
        second=rng.randint(0, 59),
        microsecond=0,
    )


def seed_volume(session: Session, rng: random.Random) -> None:
    delivery_count = _count(session, SupplyDelivery)
    if delivery_count >= MIN_DELIVERIES:
        print(
            f"Volume seed skipped: supply_deliveries already has {delivery_count} rows "
            f"(threshold {MIN_DELIVERIES})."
        )
        return

    existing_skus = {
        row
        for row in session.exec(select(MedicalSupply.sku)).all()
    }

    new_supplies: list[MedicalSupply] = []
    for i in range(1, EXTRA_PRODUCTS + 1):
        category = CATEGORIES[i % len(CATEGORIES)]
        sku = f"HCR-VOL-{category[:3].upper()}-{i:03d}"
        if sku in existing_skus:
            continue
        country = "US" if i % 2 else "UK"
        new_supplies.append(
            MedicalSupply(
                name=f"Volume test supply {category.replace('_', ' ')} #{i}",
                sku=sku,
                category=category,
                unit=UNITS[category],
                country=country,
            )
        )

    if new_supplies:
        session.add_all(new_supplies)
        session.commit()
        print(f"Inserted {len(new_supplies)} additional medical supplies.")

    supply_ids = list(session.exec(select(MedicalSupply.id)).all())
    if not supply_ids:
        raise RuntimeError("No medical supplies found; run base inventory seed first.")

    deliveries: list[SupplyDelivery] = []
    for n in range(TARGET_DELIVERIES):
        supply_id = rng.choice(supply_ids)
        deliveries.append(
            SupplyDelivery(
                supply_id=supply_id,
                quantity=rng.randint(5, 120),
                vendor_name=rng.choice(VENDORS),
                clinic_id=rng.randint(1, 12),
                created_at=_random_created_at(rng),
                user_uuid=SEED_USER_UUID,
            )
        )
        if len(deliveries) >= BATCH_SIZE:
            session.add_all(deliveries)
            session.commit()
            deliveries.clear()

    if deliveries:
        session.add_all(deliveries)
        session.commit()

    consumptions: list[SupplyConsumption] = []
    for n in range(TARGET_CONSUMPTIONS):
        supply_id = rng.choice(supply_ids)
        consumptions.append(
            SupplyConsumption(
                supply_id=supply_id,
                quantity=rng.randint(1, 40),
                consumption_type=rng.choice(CONSUMPTION_TYPES),
                clinic_id=rng.randint(1, 12),
                created_at=_random_created_at(rng),
                user_uuid=SEED_USER_UUID,
            )
        )
        if len(consumptions) >= BATCH_SIZE:
            session.add_all(consumptions)
            session.commit()
            consumptions.clear()

    if consumptions:
        session.add_all(consumptions)
        session.commit()

    supplies_n = _count(session, MedicalSupply)
    deliveries_n = _count(session, SupplyDelivery)
    consumptions_n = _count(session, SupplyConsumption)
    print(
        "Volume seed completed: "
        f"{supplies_n} supplies, {deliveries_n} deliveries, {consumptions_n} consumptions."
    )


def main() -> None:
    if not is_inventory_db_configured():
        raise SystemExit(
            "Database not configured. Set DATABASE_URL or SUPABASE_DB_* in .env"
        )

    init_inventory_db()
    rng = random.Random(42)
    with Session(get_engine()) as session:
        seed_volume(session, rng)


if __name__ == "__main__":
    main()
