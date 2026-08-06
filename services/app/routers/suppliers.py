"""Supplier Directory HTTP endpoints for HealthCore.

The router only orchestrates HTTP; persistence and rules live in domain/models.
"""
from fastapi import APIRouter, HTTPException, Query

from services.app.domain.supplier_service import (
    SupplierNotFoundError,
    create_supplier,
    delete_supplier,
    get_supplier,
    list_suppliers,
    update_supplier_rate,
    update_supplier_status,
)
from services.app.models.supplier import (
    Supplier,
    SupplierCreate,
    SupplierRateUpdate,
    SupplierStatusUpdate,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("", response_model=Supplier, status_code=201)
def create_supplier_endpoint(payload: SupplierCreate):
    """Register a new supplier. Rejects invalid data with 422."""
    return create_supplier(payload)


@router.get("", response_model=list[Supplier])
def list_suppliers_endpoint(
    country: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    """List all suppliers, optionally filtered by country and/or category."""
    return list_suppliers(country=country, category=category)


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier_endpoint(supplier_id: int):
    """Get a single supplier by ID. Returns 404 if not found."""
    try:
        return get_supplier(supplier_id)
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")


@router.patch("/{supplier_id}/rate", response_model=Supplier)
def update_supplier_rate_endpoint(supplier_id: int, payload: SupplierRateUpdate):
    """Update a supplier's monthly rate and record the timestamp."""
    try:
        return update_supplier_rate(supplier_id, payload)
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")


@router.patch("/{supplier_id}/status", response_model=Supplier)
def update_supplier_status_endpoint(supplier_id: int, payload: SupplierStatusUpdate):
    """Activate or suspend a supplier. Rejects invalid status with 422."""
    try:
        return update_supplier_status(supplier_id, payload)
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")


@router.delete("/{supplier_id}", status_code=200)
def delete_supplier_endpoint(supplier_id: int):
    """Delete a supplier from the directory. Returns 404 if not found."""
    try:
        delete_supplier(supplier_id)
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"detail": "Supplier deleted"}
