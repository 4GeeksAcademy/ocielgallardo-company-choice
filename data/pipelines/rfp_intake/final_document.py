"""Final proposal synthesizer — runs only after clean approvals (no PHI)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from data.pipelines.rfp_intake.departments import DEPARTMENTS, KNOWN_DEPARTMENTS
from data.pipelines.rfp_intake.guidelines import currency_for_country


class FinalDocumentError(ValueError):
    """Raised when synthesis preconditions fail."""


def _section_has_phi(section: dict[str, Any]) -> bool:
    if bool(section.get("contains_phi")):
        return True
    evals = section.get("evaluation_results") or {}
    return bool(evals.get("contains_phi"))


def synthesize_final_document(
    *,
    ticket_id: str,
    metadata: dict[str, Any],
    sections: dict[str, dict[str, Any]],
    approvals: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Concatenate approved drafts + metadata header.

    Refuses if any section has PHI or compliance is not approved.
    """
    approvals = approvals or {}
    for dept_id, section in sections.items():
        if _section_has_phi(section):
            raise FinalDocumentError(
                f"Cannot synthesize: department '{dept_id}' still has contains_phi=true"
            )

    compliance_approval = (approvals.get("compliance") or {}).get("approval_status")
    if compliance_approval != "approved":
        # Fall back to section-level field if approvals map not provided.
        compliance_section = sections.get("compliance") or {}
        if compliance_section.get("approval_status") != "approved":
            raise FinalDocumentError(
                "Cannot synthesize: compliance must be approved before final document"
            )

    for dept_id in KNOWN_DEPARTMENTS:
        section = sections.get(dept_id) or {}
        status = (approvals.get(dept_id) or {}).get("approval_status") or section.get(
            "approval_status"
        )
        if status != "approved":
            raise FinalDocumentError(
                f"Cannot synthesize: department '{dept_id}' is not approved (status={status})"
            )
        if not (section.get("draft_content") or "").strip():
            raise FinalDocumentError(
                f"Cannot synthesize: department '{dept_id}' has empty draft_content"
            )

    country = metadata.get("client_country")
    currency = currency_for_country(country)
    generated_at = datetime.now(timezone.utc)
    client = metadata.get("client_name") or "Unknown client"
    program = metadata.get("program_type") or "N/A"
    population = metadata.get("covered_population") or "N/A"
    deadline = metadata.get("deadline") or "N/A"

    section_payload: dict[str, Any] = {}
    body_parts: list[str] = []
    for dept_id in KNOWN_DEPARTMENTS:
        section = sections[dept_id]
        owner = DEPARTMENTS[dept_id]["owner"]
        name = DEPARTMENTS[dept_id]["name"]
        draft = str(section.get("draft_content") or "").strip()
        section_payload[dept_id] = {
            "department_id": dept_id,
            "name": name,
            "owner": owner,
            "draft_content": draft,
            "approver": (approvals.get(dept_id) or {}).get("approver")
            or section.get("approver"),
        }
        body_parts.append(f"## {name} ({owner})\n\n{draft}\n")

    header = "\n".join(
        [
            "# HealthCore Institutional Proposal",
            "",
            f"- **Ticket:** `{ticket_id}`",
            f"- **Client:** {client}",
            f"- **Country:** {country or 'N/A'}",
            f"- **Currency:** {currency}",
            f"- **Program:** {program}",
            f"- **Covered population:** {population}",
            f"- **Deadline:** {deadline}",
            f"- **Generated at (UTC):** {generated_at.isoformat()}",
            "",
            "---",
            "",
        ]
    )
    content_markdown = header + "\n".join(body_parts)

    return {
        "ticket_id": ticket_id,
        "sections": section_payload,
        "currency": currency,
        "generated_at": generated_at,
        "content_markdown": content_markdown,
    }


__all__ = ["FinalDocumentError", "synthesize_final_document"]
