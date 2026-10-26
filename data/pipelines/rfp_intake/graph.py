"""Dedicated LangGraph for RFP intake (not mixed with CX agent_graph).

Orchestrator → parallel department workers (ThreadPool) → synthesizer.
Worker *agents* are separate modules; the graph keeps a deterministic barrier
so synthesizer never runs on a partial fan-in.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from data.pipelines.rfp_intake.classifier import classify_rfp
from data.pipelines.rfp_intake.convert import pdf_to_markdown
from data.pipelines.rfp_intake.departments import KNOWN_DEPARTMENTS
from data.pipelines.rfp_intake.metadata import extract_metadata
from data.pipelines.rfp_intake.orchestrator import plan_workstreams
from data.pipelines.rfp_intake.phi import detect_and_redact_phi
from data.pipelines.rfp_intake.readability import compute_readability_metrics
from data.pipelines.rfp_intake.state import RfpIntakeState
from data.pipelines.rfp_intake.synthesizer import synthesize_handoff
from data.pipelines.rfp_intake.workers import analyze_department

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def convert_node(state: RfpIntakeState) -> dict[str, Any]:
    ticket_id = state["ticket_id"]
    pdf_path = Path(state["pdf_path"])
    if not pdf_path.is_absolute():
        pdf_path = _REPO_ROOT / pdf_path
    md_rel = f"data/raw/rfp/{ticket_id}.md"
    md_path = _REPO_ROOT / md_rel
    markdown = pdf_to_markdown(pdf_path, md_path)
    phi = detect_and_redact_phi(markdown)
    if phi["contains_phi"]:
        md_path.write_text(phi["text"], encoding="utf-8")
        markdown = phi["text"]
    readability = compute_readability_metrics(markdown)
    return {
        "markdown": markdown,
        "markdown_path": md_rel.replace("\\", "/"),
        "contains_phi": bool(phi["contains_phi"]),
        "readability": readability,
    }


def classify_node(state: RfpIntakeState) -> dict[str, Any]:
    result = classify_rfp(state.get("markdown") or "")
    payload: dict[str, Any] = {"classification": result.to_dict()}
    if not result.is_rfp:
        payload["status"] = "discarded"
        payload["discard_reason"] = result.reason
    return payload


def route_after_classify(state: RfpIntakeState) -> Literal["discard", "orchestrate"]:
    classification = state.get("classification") or {}
    if classification.get("is_rfp"):
        return "orchestrate"
    return "discard"


def discard_node(state: RfpIntakeState) -> dict[str, Any]:
    return {
        "status": "discarded",
        "discard_reason": state.get("discard_reason")
        or (state.get("classification") or {}).get("reason")
        or "Not a valid institutional RFP",
    }


def orchestrate_node(state: RfpIntakeState) -> dict[str, Any]:
    metadata = extract_metadata(state.get("markdown") or "")
    if state.get("contains_phi"):
        metadata["contains_phi"] = True
    plan = plan_workstreams(state.get("markdown") or "", metadata)
    return {
        "metadata": metadata,
        "workstreams": plan["workstreams"],
        "orchestrator_open_questions": plan["open_questions"],
        "unknown_departments": plan["unknown_departments"],
        "worker_results": {},
    }


def workers_parallel_node(state: RfpIntakeState) -> dict[str, Any]:
    """Run revenue / clinical / compliance workers concurrently (separate agents)."""
    workstreams = state.get("workstreams") or {}
    metadata = state.get("metadata") or {}
    orch_q = list(state.get("orchestrator_open_questions") or [])
    results: dict[str, dict[str, Any]] = {}

    def _run(dept_id: str) -> tuple[str, dict[str, Any]]:
        return dept_id, analyze_department(
            dept_id,
            workstreams.get(dept_id, ""),
            metadata,
            orchestrator_questions=orch_q,
        )

    with ThreadPoolExecutor(max_workers=len(KNOWN_DEPARTMENTS)) as pool:
        futures = [pool.submit(_run, dept_id) for dept_id in KNOWN_DEPARTMENTS]
        for fut in as_completed(futures):
            dept_id, result = fut.result()
            results[dept_id] = result

    return {"worker_results": results}


def synthesize_node(state: RfpIntakeState) -> dict[str, Any]:
    handoff = synthesize_handoff(
        state["ticket_id"],
        state.get("metadata") or {},
        state.get("worker_results") or {},
        orchestrator_open_questions=list(state.get("orchestrator_open_questions") or []),
    )
    return {
        "handoff_payload": handoff,
        "status": "intake_complete",
        "contains_phi": bool(handoff.get("contains_phi")),
    }


def build_graph():
    builder = StateGraph(RfpIntakeState)
    builder.add_node("convert", convert_node)
    builder.add_node("classify", classify_node)
    builder.add_node("discard", discard_node)
    builder.add_node("orchestrate", orchestrate_node)
    builder.add_node("workers_parallel", workers_parallel_node)
    builder.add_node("synthesize", synthesize_node)

    builder.add_edge(START, "convert")
    builder.add_edge("convert", "classify")
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {"discard": "discard", "orchestrate": "orchestrate"},
    )
    builder.add_edge("discard", END)
    builder.add_edge("orchestrate", "workers_parallel")
    builder.add_edge("workers_parallel", "synthesize")
    builder.add_edge("synthesize", END)
    return builder.compile()


graph = build_graph()


def run_intake_graph(*, ticket_id: str, pdf_path: str) -> dict[str, Any]:
    """Execute the rfp_intake graph once for a ticket."""
    initial: RfpIntakeState = {
        "ticket_id": ticket_id,
        "pdf_path": pdf_path,
        "worker_results": {},
        "status": "analyzing",
    }
    final = graph.invoke(initial)
    return dict(final)
