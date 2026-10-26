"""LangGraph state for the dedicated rfp_intake graph."""

from __future__ import annotations

from typing import Any, TypedDict


class RfpIntakeState(TypedDict, total=False):
    ticket_id: str
    pdf_path: str
    markdown_path: str
    markdown: str
    contains_phi: bool
    readability: dict[str, Any]
    classification: dict[str, Any]
    metadata: dict[str, Any]
    workstreams: dict[str, str]
    orchestrator_open_questions: list[str]
    unknown_departments: list[str]
    worker_results: dict[str, dict[str, Any]]
    handoff_payload: dict[str, Any]
    status: str
    discard_reason: str
    error: str
