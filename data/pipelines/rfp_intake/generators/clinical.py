"""Clinical Operations generator — feasibility section (Dr. Marcus Reid)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.generators._rag_context import (
    aspects_block,
    fetch_grounding_snippets,
    format_grounding,
)
from data.pipelines.rfp_intake.guidelines import SECTION_OUTLINES
from data.pipelines.rfp_intake.llm import chat_json, draft_llm_enabled


def generate_clinical_section(
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
        "department_id": "clinical",
        "owner": "Dr. Marcus Reid",
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
    program = metadata.get("program_type") or "institutional health program"
    population = metadata.get("covered_population")
    aspects_text = " ".join(str(a) for a in key_aspects).lower()

    delivery = []
    if "on-site" in aspects_text or "onsite" in aspects_text:
        delivery.append("On-site delivery model indicated — staff clinic roster for campus coverage.")
    if "referral" in aspects_text or "satellite" in aspects_text:
        delivery.append("Referral / satellite partnership cues — validate network clinics and triage paths.")
    if not delivery:
        delivery.append("Delivery model to confirm against Part 1 aspects during capacity planning.")

    capacity = (
        f"Capacity planning targets the stated covered population of **{population}**."
        if population
        else "Population unknown in Part 1 — Clinical will not commit clinic capacity until volume is clarified."
    )

    snippets = grounding_snippets
    if snippets is None:
        snippets = fetch_grounding_snippets(
            "HealthCore clinic capacity occupational health wellness staffing model"
        )
    grounding = format_grounding(snippets)
    feedback_block = (
        f"\n\n### Revision notes from evaluator\n{feedback_for_generator}\n"
        if feedback_for_generator.strip()
        else ""
    )
    outline = "\n".join(f"- {item}" for item in SECTION_OUTLINES["clinical"])

    return f"""## Clinical Operations — Feasibility Section

**Client:** {client}  
**Program:** {program}  
**Owner:** Dr. Marcus Reid (Clinical Operations)

### Clinical feasibility
- Assess staffing and clinic readiness for **{program}** at {client}.
- {capacity}
- This section discusses institutional service capacity only — **no patient identifiers or clinical case narratives**.

### Delivery model
{chr(10).join(f"- {d}" for d in delivery)}

### Part 1 key aspects incorporated
{aspects_block(key_aspects)}

### Open clinical questions
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
            "You refine HealthCore Clinical Operations proposal sections. "
            "Return JSON {draft_content: string}. Never invent PHI or uncovered headcount."
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
