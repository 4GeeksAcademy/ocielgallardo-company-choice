"""Department worker agents — analyze extracts only; never invent volumes/PHI."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.dedupe import dedupe_questions
from data.pipelines.rfp_intake.departments import DEPARTMENTS
from data.pipelines.rfp_intake.llm import chat_json
from data.pipelines.rfp_intake.phi import detect_and_redact_phi


def _base_open_questions(
    department_id: str,
    metadata: dict[str, Any],
    orchestrator_questions: list[str],
) -> list[str]:
    questions = list(orchestrator_questions)
    if department_id in {"revenue", "clinical"} and not metadata.get("covered_population"):
        q = "What covered population / headcount should this contract assume? (not stated in RFP)"
        if q not in questions:
            questions.append(q)
    return questions


def analyze_department_heuristic(
    department_id: str,
    extract: str,
    metadata: dict[str, Any],
    *,
    orchestrator_questions: list[str] | None = None,
) -> dict[str, Any]:
    """Pure worker logic used by tests and as LLM fallback."""
    info = DEPARTMENTS[department_id]
    phi = detect_and_redact_phi(extract)
    safe_extract = phi["text"]
    aspects: list[str] = []
    open_questions = _base_open_questions(
        department_id, metadata, orchestrator_questions or []
    )

    client = metadata.get("client_name") or "Unknown client"
    country = metadata.get("client_country")
    program = metadata.get("program_type") or "unspecified program"
    population = metadata.get("covered_population")
    budget = metadata.get("budget_range")
    deadline = metadata.get("deadline")

    if department_id == "revenue":
        currency = "USD" if country == "US" else "GBP" if country == "UK" else "TBD"
        aspects.append(f"Client: {client} ({country or 'country TBD'})")
        aspects.append(f"Program type: {program}")
        aspects.append(f"Quote currency: {currency}")
        if population:
            aspects.append(f"Covered population stated: {population}")
        else:
            aspects.append("Covered population: not stated — do not invent headcount")
        if budget:
            aspects.append(f"Budget signal in RFP: {budget}")
        else:
            open_questions.append("Is there a reference budget or NTE for pricing?")
        if deadline:
            aspects.append(f"Response / contract deadline signal: {deadline}")
        aspects.append(f"Owner contact: {info['owner']} (Revenue Cycle)")

    elif department_id == "clinical":
        aspects.append(f"Assess clinical feasibility for {program} at {client}")
        if population:
            aspects.append(f"Capacity must cover stated population: {population}")
        else:
            aspects.append("Population unknown — confirm sites/staff before committing capacity")
        if "on-site" in safe_extract.lower() or "onsite" in safe_extract.lower():
            aspects.append("On-site delivery mentioned — evaluate clinic staffing model")
        if "satellite" in safe_extract.lower() or "referral" in safe_extract.lower():
            aspects.append("Referral / satellite clinic partnership cues present")
        aspects.append(f"Owner contact: {info['owner']} (Clinical Operations)")

    elif department_id == "compliance":
        aspects.append("Compliance review is mandatory for every institutional proposal")
        if country == "US":
            aspects.append("US client → require Business Associate Agreement (BAA) clause")
        elif country == "UK":
            aspects.append("UK client → require Data Processing Agreement (DPA) / UK GDPR")
        else:
            aspects.append("Client country unclear → confirm US (BAA) vs UK (DPA) before drafting")
            open_questions.append("Confirm client country for BAA vs DPA instrument")
        if phi["contains_phi"]:
            aspects.append(
                "PHI-like content detected in source extract — redacted; flag for Compliance human review"
            )
            open_questions.append(
                "Source document contained PHI-like content; Claire Whitfield must review before Part 2"
            )
        aspects.append(f"Owner contact: {info['owner']} (Compliance)")

    # Never echo raw PHI into aspects
    aspects = [a for a in aspects if "patient" not in a.lower() or "PHI" in a]

    return {
        "department_id": department_id,
        "owner": info["owner"],
        "key_aspects": aspects,
        "open_questions": dedupe_questions(open_questions),
        "contains_phi": bool(phi["contains_phi"]),
        "extract_used": safe_extract[:2000],
    }


def analyze_department(
    department_id: str,
    extract: str,
    metadata: dict[str, Any],
    *,
    orchestrator_questions: list[str] | None = None,
) -> dict[str, Any]:
    base = analyze_department_heuristic(
        department_id,
        extract,
        metadata,
        orchestrator_questions=orchestrator_questions,
    )
    phi = detect_and_redact_phi(extract)
    llm = chat_json(
        system=(
            f"You are the {department_id} analyst for HealthCore. "
            "Given metadata + a department extract, return JSON "
            "{key_aspects: string[], open_questions: string[], contains_phi: bool}. "
            "Never invent headcount, budget, or patient identifiers. "
            "If a figure is missing, put a question in open_questions."
        ),
        user=(
            f"metadata={metadata}\n\nextract:\n{phi['text'][:8000]}\n\n"
            f"seed_aspects={base['key_aspects']}"
        ),
    )
    if not llm:
        return base
    aspects = llm.get("key_aspects")
    questions = llm.get("open_questions")
    if isinstance(aspects, list) and aspects:
        base["key_aspects"] = [str(a)[:500] for a in aspects if a]
    if isinstance(questions, list):
        merged = list(base["open_questions"])
        for q in questions:
            qs = str(q)
            if qs and qs not in merged:
                merged.append(qs)
        base["open_questions"] = dedupe_questions(merged)
    if llm.get("contains_phi") is True or phi["contains_phi"]:
        base["contains_phi"] = True
    return base
