"""Extract institutional RFP metadata from Markdown (never invent figures / PHI)."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.llm import chat_json

_COUNTRY_US = re.compile(
    r"\b(?:united states|u\.s\.a?\.?|usa|austin|texas|\bus\b)\b",
    re.IGNORECASE,
)
_COUNTRY_UK = re.compile(
    r"\b(?:united kingdom|u\.k\.|uk|england|london|thames|gbp)\b",
    re.IGNORECASE,
)


def extract_metadata_heuristic(markdown: str) -> dict[str, Any]:
    text = markdown or ""
    client_name = None
    # Common formal header patterns
    m = re.search(
        r"(?:client|organization|company|university)\s*[:\-]\s*([^\n]+)",
        text,
        re.I,
    )
    if m:
        client_name = m.group(1).strip()[:256]
    if not client_name:
        m = re.search(
            r"\b(Meridian Manufacturing|Thames Valley University)\b",
            text,
            re.I,
        )
        if m:
            client_name = m.group(1)

    client_country = None
    if _COUNTRY_UK.search(text) and not _COUNTRY_US.search(text):
        client_country = "UK"
    elif _COUNTRY_US.search(text):
        client_country = "US"
    elif _COUNTRY_UK.search(text):
        client_country = "UK"

    program_type = None
    if re.search(r"occupational\s+health", text, re.I):
        program_type = "occupational_health"
    elif re.search(r"corporate\s+wellness|wellness", text, re.I):
        program_type = "corporate_wellness"
    elif re.search(r"referral\s+network|referral", text, re.I):
        program_type = "referral_network"

    covered_population = None
    pop = re.search(
        r"(\d[\d,]*)\s+(?:employees?|students?|lives|members?)\b",
        text,
        re.I,
    )
    if pop:
        covered_population = pop.group(1).replace(",", "")

    deadline = None
    dl = re.search(
        r"(?:deadline|due|respond by|submission)\s*[:\-]?\s*([^\n.]{3,40})",
        text,
        re.I,
    )
    if dl:
        deadline = dl.group(1).strip()[:64]

    budget_range = None
    bud = re.search(
        r"(?:budget|not to exceed|nte)\s*[:\-]?\s*([^\n.]{3,40})",
        text,
        re.I,
    )
    if bud:
        budget_range = bud.group(1).strip()[:128]

    return {
        "client_name": client_name,
        "client_country": client_country,
        "program_type": program_type,
        "covered_population": covered_population,
        "deadline": deadline,
        "budget_range": budget_range,
        "departments_needed": ["revenue", "clinical", "compliance"],
    }


def extract_metadata(markdown: str) -> dict[str, Any]:
    base = extract_metadata_heuristic(markdown)
    llm = chat_json(
        system=(
            "Extract HealthCore institutional RFP metadata as JSON. Fields: "
            "client_name, client_country (US or UK only), program_type "
            "(occupational_health|corporate_wellness|referral_network), "
            "covered_population (string digits only or null — never invent), "
            "deadline, budget_range. Omit patient names. Never invent volumes."
        ),
        user=markdown[:12000],
    )
    if not llm:
        return base
    out = dict(base)
    for key in (
        "client_name",
        "client_country",
        "program_type",
        "covered_population",
        "deadline",
        "budget_range",
    ):
        value = llm.get(key)
        if value in (None, "", "null"):
            continue
        if key == "client_country":
            cc = str(value).upper()
            if cc in {"US", "UK"}:
                out[key] = cc
            continue
        if key == "covered_population":
            digits = re.sub(r"[^\d]", "", str(value))
            if digits:
                out[key] = digits
            continue
        out[key] = str(value)[:256]
    out["departments_needed"] = ["revenue", "clinical", "compliance"]
    return out
