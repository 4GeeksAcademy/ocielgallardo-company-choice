"""Supplier Directory endpoints for HealthCore.

Separación de responsabilidades:
- El router solo orquesta HTTP (recibir peticiones, devolver respuestas).
- database.py gestiona TinyDB.
- models.py define las reglas de validación.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from services.api.database import suppliers_table
from services.api.models import (
    Supplier,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _doc_to_response(doc) -> Supplier:
    """Convert a TinyDB document to a Supplier response model."""
    return Supplier(
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


@router.post("", response_model=Supplier, status_code=201)
def create_supplier(payload: SupplierCreate):
    """Register a new supplier. Rejects invalid data with 422."""
    doc = payload.model_dump(mode="json")
    doc["updated_at"] = None
    doc_id = suppliers_table.insert(doc)
    stored = suppliers_table.get(doc_id=doc_id)
    return _doc_to_response(stored)


@router.get("", response_model=list[Supplier])
def list_suppliers(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    """List all suppliers, optionally filtered by country and/or category."""
    results = suppliers_table.all()

    if country:
        results = [r for r in results if r.get("country") == country]
    if category:
        results = [r for r in results if category in r.get("categories", [])]

    return [_doc_to_response(r) for r in results]


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: int):
    """Get a single supplier by ID. Returns 404 if not found."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return _doc_to_response(doc)


@router.patch("/{supplier_id}/rate", response_model=Supplier)
def update_supplier_rate(supplier_id: int, payload: SupplierRateUpdate):
    """Update a supplier's monthly rate and record the timestamp."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    now = datetime.now(timezone.utc).isoformat()
    suppliers_table.update(
        {"monthly_rate": payload.monthly_rate, "updated_at": now},
        doc_ids=[supplier_id],
    )
    updated = suppliers_table.get(doc_id=supplier_id)
    return _doc_to_response(updated)


@router.patch("/{supplier_id}/status", response_model=Supplier)
def update_supplier_status(supplier_id: int, payload: SupplierStatusUpdate):
    """Activate or suspend a supplier. Rejects invalid status with 422."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    suppliers_table.update(
        {"status": payload.status.value},
        doc_ids=[supplier_id],
    )
    updated = suppliers_table.get(doc_id=supplier_id)
    return _doc_to_response(updated)


@router.delete("/{supplier_id}", status_code=200)
def delete_supplier(supplier_id: int):
    """Delete a supplier from the directory. Returns 404 if not found."""
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    suppliers_table.remove(doc_ids=[supplier_id])
    return {"detail": "Supplier deleted"}