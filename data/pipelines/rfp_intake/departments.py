"""HealthCore departments for Milestone 9 RFP intake (BRIEFING §2.1)."""

from __future__ import annotations

from typing import TypedDict


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
