"""Revenue Cycle generator — financial terms section (Tom Callahan)."""

from __future__ import annotations

from typing import Any

from data.pipelines.rfp_intake.generators._rag_context import (
    aspects_block,
    fetch_grounding_snippets,
    format_grounding,
)
from data.pipelines.rfp_intake.guidelines import SECTION_OUTLINES, currency_for_country
from data.pipelines.rfp_intake.llm import chat_json, draft_llm_enabled


def generate_revenue_section(
    *,
    metadata: dict[str, Any],
    key_aspects: list[Any],
    open_questions: list[Any] | None = None,
    feedback_for_generator: str = "",
    grounding_snippets: list[str] | None = None,
) -> dict[str, Any]:
    """Produce the Revenue proposal section from intake handoff only (no PDF)."""
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
        "department_id": "revenue",
        "owner": "Tom Callahan",
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
    program = metadata.get("program_type") or "institutional health program"
    population = metadata.get("covered_population")
    deadline = metadata.get("deadline")
    budget = metadata.get("budget_range")

    snippets = grounding_snippets
    if snippets is None:
        snippets = fetch_grounding_snippets(
            f"HealthCore occupational health pricing payment terms {currency} institutional contract"
        )
    grounding = format_grounding(snippets)

    pop_line = (
        f"- Covered population stated in intake: **{population}** (do not invent additional headcount)."
        if population
        else "- Covered population: **not stated in Part 1** — pricing assumes clarification before binding quote."
    )
    budget_line = (
        f"- Budget signal from RFP: {budget}."
        if budget
        else "- No reference budget in Part 1; propose transparent fee schedule pending discovery."
    )
    deadline_line = f"- Response / term signal: {deadline}." if deadline else "- Contract term: align to 12-month institutional standard unless clarified."

    feedback_block = (
        f"\n\n### Revision notes from evaluator\n{feedback_for_generator}\n"
        if feedback_for_generator.strip()
        else ""
    )

    outline = "\n".join(f"- {item}" for item in SECTION_OUTLINES["revenue"])

    return f"""## Revenue Cycle — Economic Proposal Section

**Client:** {client} ({country or "country TBD"})  
**Program:** {program}  
**Quote currency:** **{currency}**  
**Owner:** Tom Callahan (Revenue Cycle)

### Scope of commercial terms
{pop_line}
{budget_line}
{deadline_line}

### Payment structure
- Fees quoted exclusively in **{currency}** per HealthCore country policy.
- Milestone billing: discovery / mobilization, steady-state service months, close-out.
- No patient-level billing identifiers appear in this institutional proposal.

### Part 1 key aspects incorporated
{aspects_block(key_aspects)}

### Open commercial questions
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
            "You refine HealthCore Revenue Cycle proposal sections. "
            "Return JSON {draft_content: string}. Never invent PHI, patient names, "
            "or headcount not present in metadata. Keep currency USD for US and GBP for UK."
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
