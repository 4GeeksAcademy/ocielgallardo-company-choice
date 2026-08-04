"""Pydantic models and enums for the HealthCore supplier directory."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, model_validator


# ==========================================================
# Enums
# ==========================================================

class Country(str, Enum):
    USA = "USA"
    UK = "UK"


class Currency(str, Enum):
    USD = "USD"
    GBP = "GBP"


class SupplierStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class SupplierCategory(str, Enum):
    MEDICAL_SUPPLIES = "medical_supplies"
    LABORATORY_SERVICES = "laboratory_services"
    PHARMACEUTICAL = "pharmaceutical"
    CLINICAL_SOFTWARE = "clinical_software"
    IT_INFRASTRUCTURE = "it_infrastructure"
    HR_AND_PAYROLL_SOFTWARE = "hr_and_payroll_software"
    CLEANING_AND_FACILITIES = "cleaning_and_facilities"
    PATIENT_COMMUNICATION = "patient_communication"
    BILLING_AND_CODING_SOFTWARE = "billing_and_coding_software"
    TRAINING_PLATFORMS = "training_platforms"


class ComplianceAgreement(str, Enum):
    BAA = "BAA"
    DPA = "DPA"
    BOTH = "both"


# ==========================================================
# Base model
# ==========================================================

class SupplierBase(BaseModel):
    """Common supplier fields."""

    name: str = Field(min_length=1)
    country: Country
    categories: list[SupplierCategory] = Field(min_length=1)
    monthly_rate: float = Field(gt=0)
    currency: Currency
    status: SupplierStatus = SupplierStatus.ACTIVE
    compliance_agreement: ComplianceAgreement | None = None
    contract_renewal_date: date | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None


# ==========================================================
# Create supplier
# ==========================================================

class SupplierCreate(SupplierBase):
    """Payload to register a new supplier."""

    @model_validator(mode="after")
    def currency_must_match_country(self):
        expected = Currency.USD if self.country == Country.USA else Currency.GBP

        if self.currency != expected:
            raise ValueError(
                f"currency must be '{expected.value}' when country is '{self.country.value}'"
            )

        return self


# ==========================================================
# Response model
# ==========================================================

class Supplier(SupplierCreate):
    """Supplier returned by the API."""

    id: int
    updated_at: datetime


# ==========================================================
# PATCH models
# ==========================================================

class SupplierRateUpdate(BaseModel):
    """Payload to update the supplier monthly rate."""

    monthly_rate: float = Field(gt=0)


class SupplierStatusUpdate(BaseModel):
    """Payload to activate or suspend a supplier."""

    status: SupplierStatus