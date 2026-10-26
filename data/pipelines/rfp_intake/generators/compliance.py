"""Compliance generator — regulatory section (Claire Whitfield)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.generators._rag_context import (
    aspects_block,
    fetch_grounding_snippets,
    format_grounding,
)
from data.pipelines.rfp_intake.guidelines import SECTION_OUTLINES, currency_for_country
from data.pipelines.rfp_intake.llm import chat_json, draft_llm_enabled


def generate_compliance_section(
    *,
    metadata: dict[str, Any],
    key_aspects: list[Any],
    open_questions: list[Any] | None = None,
    feedback_for_generator: str = "",
    grounding_snippets: list[str] | None = None,
) -> dict[str, Any]:
    draft = _heuristic_draft(
        metadata=metadata,
        key_aspects=key_aspects,
        open_questions=open_questions or [],
        feedback_for_generator=feedback_for_generator,
        grounding_snippets=grounding_snippets,
    )
    llm_draft = None
    if draft_llm_enabled():
        llm_draft = _llm_refine(draft, metadata, key_aspects, feedback_for_generator)
    return {
        "department_id": "compliance",
        "owner": "Claire Whitfield",
        "draft_content": llm_draft or draft,
    }


def _heuristic_draft(
    *,
    metadata: dict[str, Any],
    key_aspects: list[Any],
    open_questions: list[Any],
    feedback_for_generator: str,
    grounding_snippets: list[str] | None = None,
) -> str:
    client = metadata.get("client_name") or "Institutional client"
    country = metadata.get("client_country")
    currency = currency_for_country(country)

    if country == "US":
        instrument = (
            "**Business Associate Agreement (BAA)** under HIPAA will be executed before "
            "any protected health information is processed on behalf of the client."
        )
        regime = "United States / HIPAA"
    elif country == "UK":
        instrument = (
            "**Data Processing Agreement (DPA)** referencing **UK GDPR** will be executed "
            "before personal data processing begins."
        )
        regime = "United Kingdom / UK GDPR"
    else:
        instrument = (
            "Client country unclear in Part 1 — Compliance will confirm BAA (US) vs DPA/UK GDPR "
            "(UK) before Part 3 approval."
        )
        regime = "Country TBD"

    snippets = grounding_snippets
    if snippets is None:
        snippets = fetch_grounding_snippets(
            "HealthCore HIPAA BAA UK GDPR data processing agreement privacy policy"
        )
    grounding = format_grounding(snippets)
    feedback_block = (
        f"\n\n### Revision notes from evaluator\n{feedback_for_generator}\n"
        if feedback_for_generator.strip()
        else ""
    )
    outline = "\n".join(f"- {item}" for item in SECTION_OUTLINES["compliance"])
    phi_flag = bool(metadata.get("contains_phi"))
    phi_note = (
        "Part 1 flagged PHI-like content in the source RFP — this proposal section contains "
        "**no patient names or diagnoses**; Claire Whitfield must review before Part 3."
        if phi_flag
        else "This proposal section contains **no patient names, diagnoses, or patient identifiers**."
    )

    return f"""## Compliance and Data Governance — Regulatory Section

**Client:** {client} ({country or "country TBD"})  
**Regulatory regime:** {regime}  
**Commercial currency alignment:** {currency}  
**Owner:** Claire Whitfield (Compliance and Data Governance)

### Mandatory compliance posture
- Compliance review is **mandatory** for every institutional HealthCore proposal.
- {instrument}
- {phi_note}

### Part 1 key aspects incorporated
{aspects_block(key_aspects)}

### Open compliance questions
{aspects_block(open_questions) if open_questions else "- None recorded in Part 1."}

### Required outline checklist
{outline}
{grounding}{feedback_block}
"""


def _llm_refine(
    draft: str,
    metadata: dict[str, Any],
    key_aspects: list[Any],
    feedback: str,
) -> str | None:
    result = chat_json(
        system=(
            "You refine HealthCore Compliance proposal sections. "
            "Return JSON {draft_content: string}. US clients need BAA; UK clients need DPA/UK GDPR. "
            "Never include patient names or diagnoses."
        ),
        user=(
            f"metadata={metadata}\naspects={key_aspects}\nfeedback={feedback}\n"
            f"current_draft:\n{draft[:6000]}"
        ),
        temperature=0.2,
    )
    if not result:
        return None
    content = result.get("draft_content")
    return str(content).strip() if content else None
