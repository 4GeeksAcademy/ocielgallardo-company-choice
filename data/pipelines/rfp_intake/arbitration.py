"""Part 3 conflict arbitration — fixed BRIEFING triggers (no LLM vote)."""

from __future__ import annotations

import re
from typing import Any

from data.pipelines.rfp_intake.departments import DEPARTMENT_OWNERS

TRIGGER_PHI = "phi-detected"
TRIGGER_BAA_DPA = "baa-dpa-mismatch"
TRIGGER_CAPACITY = "capacity-vs-population"

_CAPACITY_COMMIT_RE = re.compile(
    r"(can cover|sufficient capacity|capacity (is )?adequate|"
    r"staff(ing)? (is )?sufficient|we can support)",
    re.IGNORECASE,
)
_CAPACITY_SHORTFALL_RE = re.compile(
    r"(cannot cover|insufficient capacity|capacity shortfall|"
    r"unable to (staff|cover)|not enough (clinic|staff))",
    re.IGNORECASE,
)
_POPULATION_NUM_RE = re.compile(r"(\d[\d,]*)\s*(employees|staff|lives|members|students)", re.I)


def _section_has_phi(section: dict[str, Any]) -> bool:
    if bool(section.get("contains_phi")):
        return True
    evals = section.get("evaluation_results") or {}
    if bool(evals.get("contains_phi")):
        return True
    compliance = evals.get("compliance") or {}
    if isinstance(compliance, dict) and bool(compliance.get("contains_phi")):
        return True
    return False


def _draft_text(section: dict[str, Any]) -> str:
    return str(section.get("draft_content") or "")


def _baa_present(text: str) -> bool:
    lower = text.lower()
    if re.search(r"\b(no|without|missing|lacks?)\s+baa\b", lower):
        return False
    if "business associate" in lower:
        return True
    return bool(re.search(r"\bbaa\b", lower))


def _dpa_present(text: str) -> bool:
    lower = text.lower()
    if re.search(r"\b(no|without|missing|lacks?)\s+dpa\b", lower):
        return False
    if "data processing" in lower or "uk gdpr" in lower:
        return True
    return bool(re.search(r"\bdpa\b", lower))


def _detect_baa_dpa_mismatch(
    *,
    client_country: str | None,
    sections: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    country = (client_country or "").upper()
    if country not in {"US", "UK"}:
        return None

    targets: list[str] = []
    compliance = sections.get("compliance") or {}
    compliance_text = _draft_text(compliance)
    all_text = " ".join(_draft_text(s) for s in sections.values())

    if country == "US":
        if not _baa_present(compliance_text) and not _baa_present(all_text):
            targets.append("compliance")
        # Wrong instrument for US (DPA without BAA) in compliance draft.
        if _dpa_present(compliance_text) and not _baa_present(compliance_text):
            if "compliance" not in targets:
                targets.append("compliance")
        for dept_id, section in sections.items():
            text = _draft_text(section)
            if _dpa_present(text) and not _baa_present(text) and dept_id != "compliance":
                if dept_id not in targets:
                    targets.append(dept_id)
    else:  # UK
        if not _dpa_present(compliance_text) and not _dpa_present(all_text):
            targets.append("compliance")
        if _baa_present(compliance_text) and not _dpa_present(compliance_text):
            if "compliance" not in targets:
                targets.append("compliance")
        for dept_id, section in sections.items():
            text = _draft_text(section)
            if _baa_present(text) and not _dpa_present(text) and dept_id != "compliance":
                if dept_id not in targets:
                    targets.append(dept_id)

    if not targets:
        return None

    return {
        "trigger_id": TRIGGER_BAA_DPA,
        "arbiter": DEPARTMENT_OWNERS["compliance"],
        "arbiter_department_id": "compliance",
        "resolution": "request_changes",
        "blocking_phi": False,
        "force_request_changes_departments": targets,
        "detail": (
            f"Country={country}: required BAA (US) or DPA/UK GDPR (UK) clause missing "
            f"or wrong instrument embedded."
        ),
    }


def _parse_population(metadata: dict[str, Any]) -> int | None:
    raw = str(metadata.get("covered_population") or "")
    match = re.search(r"(\d[\d,]*)", raw)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _detect_capacity_vs_population(
    *,
    metadata: dict[str, Any],
    sections: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    clinical = sections.get("clinical") or {}
    revenue = sections.get("revenue") or {}
    clinical_text = _draft_text(clinical)
    revenue_text = _draft_text(revenue)
    population = _parse_population(metadata)

    shortfall = bool(
        _CAPACITY_SHORTFALL_RE.search(clinical_text)
        or _CAPACITY_SHORTFALL_RE.search(revenue_text)
    )
    affirms = bool(_CAPACITY_COMMIT_RE.search(clinical_text))
    capacity_nums = [
        int(m.group(1).replace(",", ""))
        for m in _POPULATION_NUM_RE.finditer(clinical_text)
    ]
    under_capacity = bool(
        population is not None
        and capacity_nums
        and max(capacity_nums) < population
    )
    # Large stated population without an affirmative clinical capacity statement.
    large_pop_uncovered = bool(
        population is not None
        and population >= 500
        and clinical_text
        and not affirms
        and (
            str(population) in revenue_text
            or "employee" in revenue_text.lower()
            or "population" in revenue_text.lower()
        )
    )

    if not (shortfall or under_capacity or large_pop_uncovered):
        return None

    return {
        "trigger_id": TRIGGER_CAPACITY,
        "arbiter": DEPARTMENT_OWNERS["revenue"],
        "arbiter_department_id": "revenue",
        "resolution": "request_changes",
        "blocking_phi": False,
        "force_request_changes_departments": ["revenue", "clinical"],
        "detail": (
            "Clinical capacity cannot cover stated covered-population / contract volume; "
            "reduce population or add sites."
        ),
    }


def detect_conflicts(
    *,
    metadata: dict[str, Any],
    sections: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return structured conflicts for the arbitration node (fixed rules)."""
    conflicts: list[dict[str, Any]] = []

    phi_depts = [
        dept_id
        for dept_id, section in sections.items()
        if _section_has_phi(section)
    ]
    if bool(metadata.get("contains_phi")) and not phi_depts:
        phi_depts = list(sections.keys()) or ["compliance"]

    if phi_depts:
        conflicts.append(
            {
                "trigger_id": TRIGGER_PHI,
                "arbiter": DEPARTMENT_OWNERS["compliance"],
                "arbiter_department_id": "compliance",
                "resolution": "request_changes",
                "blocking_phi": True,
                "force_request_changes_departments": sorted(set(phi_depts + ["compliance"])),
                "detail": (
                    "PHI flagged on section(s): "
                    + ", ".join(sorted(set(phi_depts)))
                    + ". Synthesizer must not run until cleared."
                ),
            }
        )

    baa = _detect_baa_dpa_mismatch(
        client_country=metadata.get("client_country"),
        sections=sections,
    )
    if baa:
        conflicts.append(baa)

    # capacity-vs-population only after no PHI (BRIEFING: Tom after Compliance confirms no PHI).
    has_phi = any(c.get("blocking_phi") for c in conflicts)
    if not has_phi:
        capacity = _detect_capacity_vs_population(metadata=metadata, sections=sections)
        if capacity:
            conflicts.append(capacity)

    return conflicts


def apply_arbitration(
    *,
    metadata: dict[str, Any],
    sections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Run arbitration and return conflict list + forced request_changes map."""
    conflicts = detect_conflicts(metadata=metadata, sections=sections)
    force: dict[str, str] = {}
    blocking_phi = False
    for conflict in conflicts:
        if conflict.get("blocking_phi"):
            blocking_phi = True
        for dept_id in conflict.get("force_request_changes_departments") or []:
            force[str(dept_id)] = "request_changes"
    return {
        "conflicts": conflicts,
        "force_request_changes": force,
        "blocking_phi": blocking_phi,
        "synthesizer_blocked": blocking_phi,
    }


__all__ = [
    "TRIGGER_PHI",
    "TRIGGER_BAA_DPA",
    "TRIGGER_CAPACITY",
    "detect_conflicts",
    "apply_arbitration",
]
