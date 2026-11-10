"""HealthCore departments for Milestone 9 RFP intake (BRIEFING §2.1)."""

from __future__ import annotations

import os
from typing import Protocol, TypedDict


class DepartmentInfo(TypedDict):
    department_id: str
    name: str
    owner: str
    role: str


KNOWN_DEPARTMENTS: tuple[str, ...] = ("revenue", "clinical", "compliance")

DEPARTMENTS: dict[str, DepartmentInfo] = {
    "revenue": {
        "department_id": "revenue",
        "name": "Revenue Cycle",
        "owner": "Tom Callahan",
        "role": "Financial terms, currency, payment structure. Owns the ticket.",
    },
    "clinical": {
        "department_id": "clinical",
        "name": "Clinical Operations",
        "owner": "Dr. Marcus Reid",
        "role": "Clinical feasibility: clinics and staff capacity for the contract.",
    },
    "compliance": {
        "department_id": "compliance",
        "name": "Compliance and Data Governance",
        "owner": "Claire Whitfield",
        "role": "HIPAA/UK GDPR review; BAA or DPA by client country. Always required.",
    },
}

DEPARTMENT_OWNERS: dict[str, str] = {
    dept_id: info["owner"] for dept_id, info in DEPARTMENTS.items()
}

# Env override examples (comma-separated emails):
#   RFP_REVENUE_OWNER_EMAIL=tom@healthcore.example
#   RFP_CLINICAL_OWNER_EMAIL=marcus@healthcore.example
#   RFP_COMPLIANCE_OWNER_EMAIL=claire@healthcore.example
_DEPARTMENT_OWNER_EMAIL_ENV: dict[str, str] = {
    "revenue": "RFP_REVENUE_OWNER_EMAIL",
    "clinical": "RFP_CLINICAL_OWNER_EMAIL",
    "compliance": "RFP_COMPLIANCE_OWNER_EMAIL",
}


class _ApproverLike(Protocol):
    email: str
    role: object


def department_owner_emails(department_id: str) -> frozenset[str]:
    """Configured approver emails for a department (lowercased)."""
    env_key = _DEPARTMENT_OWNER_EMAIL_ENV.get(department_id)
    if not env_key:
        return frozenset()
    raw = os.getenv(env_key, "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def user_may_approve_department(user: _ApproverLike, department_id: str) -> bool:
    """True when the caller may resume HITL for ``department_id``.

    Admins always may. Otherwise the caller's email must appear in the
    department owner allowlist (``RFP_*_OWNER_EMAIL``). Display names in
    ``DEPARTMENT_OWNERS`` are documentation only — they are not authz.
    """
    role_value = getattr(user.role, "value", user.role)
    if str(role_value).lower() == "admin":
        return True
    email = str(getattr(user, "email", "") or "").strip().lower()
    if not email:
        return False
    return email in department_owner_emails(department_id)

# Keywords used to pull department-relevant extracts from Markdown.
DEPARTMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "budget",
        "payment",
        "currency",
        "usd",
        "gbp",
        "price",
        "pricing",
        "cost",
        "invoice",
        "contract term",
        "12-month",
        "fee",
    ),
    "clinical": (
        "clinic",
        "clinical",
        "occupational health",
        "wellness",
        "referral",
        "staff",
        "capacity",
        "on-site",
        "satellite",
        "employee",
        "student",
        "population",
    ),
    "compliance": (
        "hipaa",
        "gdpr",
        "baa",
        "dpa",
        "privacy",
        "data protection",
        "phi",
        "patient",
        "compliance",
        "regulatory",
        "uk",
        "united states",
    ),
}
