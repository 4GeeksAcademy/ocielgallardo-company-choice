"""Supplier directory business logic (TinyDB persistence)."""
from datetime import datetime, timezone

from services.app.core.database import suppliers_table
from services.app.models.supplier import (
    SupplierCreate,
    SupplierRateUpdate,
    SupplierResponse,
    SupplierStatusUpdate,
)


class SupplierNotFoundError(LookupError):
    """Raised when a supplier id does not exist in TinyDB."""


def _doc_to_response(doc) -> SupplierResponse:
    """Convert a TinyDB document to a SupplierResponse model."""
    return SupplierResponse(
        id=doc.doc_id,
        name=doc["name"],
        country=doc["country"],
        categories=doc["categories"],
        monthly_rate=doc["monthly_rate"],
        currency=doc["currency"],
        status=doc.get("status", "active"),
        updated_at=doc.get("updated_at"),
        compliance_agreement=doc.get("compliance_agreement"),
        contract_renewal_date=doc.get("contract_renewal_date"),
        contact_email=doc.get("contact_email"),
        notes=doc.get("notes"),
    )


def create_supplier(payload: SupplierCreate) -> SupplierResponse:
    """Register a new supplier."""
    doc = payload.model_dump(mode="json")
    doc["updated_at"] = None
    doc_id = suppliers_table.insert(doc)
    stored = suppliers_table.get(doc_id=doc_id)
    return _doc_to_response(stored)


def list_suppliers(
    country: str | None = None,
    category: str | None = None,
) -> list[SupplierResponse]:
    """List suppliers, optionally filtered by country and/or category."""
    results = suppliers_table.all()

    if country:
        results = [r for r in results if r.get("country") == country]
    if category:
        results = [r for r in results if category in r.get("categories", [])]

    return [_doc_to_response(r) for r in results]


def get_supplier(supplier_id: int) -> SupplierResponse:
    """Get a single supplier by ID."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise SupplierNotFoundError("Supplier not found")
    return _doc_to_response(doc)


def update_supplier_rate(
    supplier_id: int, payload: SupplierRateUpdate
) -> SupplierResponse:
    """Update a supplier's monthly rate and record the timestamp."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise SupplierNotFoundError("Supplier not found")

    now = datetime.now(timezone.utc).isoformat()
    suppliers_table.update(
        {"monthly_rate": payload.monthly_rate, "updated_at": now},
        doc_ids=[supplier_id],
    )
    updated = suppliers_table.get(doc_id=supplier_id)
    return _doc_to_response(updated)


def update_supplier_status(
    supplier_id: int, payload: SupplierStatusUpdate
) -> SupplierResponse:
    """Activate or suspend a supplier."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise SupplierNotFoundError("Supplier not found")

    suppliers_table.update(
        {"status": payload.status.value},
        doc_ids=[supplier_id],
    )
    updated = suppliers_table.get(doc_id=supplier_id)
    return _doc_to_response(updated)


def delete_supplier(supplier_id: int) -> None:
    """Delete a supplier from the directory."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise SupplierNotFoundError("Supplier not found")

    suppliers_table.remove(doc_ids=[supplier_id])
