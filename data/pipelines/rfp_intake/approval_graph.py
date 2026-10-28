"""Part 3 approval graph: guardrails → arbitration → parallel HITL → synthesizer.

Each department is its own interrupt branch. Approving department B while A is
still interrupted is a first-class behavior (true parallel, not a serial loop).

Durable checkpoints via SqliteSaver. Business truth for the UI remains in
Postgres; the checkpointer resumes graph control flow only.
"""

from __future__ import annotations

import logging
import operator
import sqlite3
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from data.pipelines.rfp_intake.arbitration import apply_arbitration
from data.pipelines.rfp_intake.departments import DEPARTMENT_OWNERS, KNOWN_DEPARTMENTS
from data.pipelines.rfp_intake.final_document import (
    FinalDocumentError,
    synthesize_final_document,
)
from data.pipelines.rfp_intake.guidelines import currency_for_country
from data.pipelines.rfp_intake.trace import make_trace_event

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKPOINT_DIR = _REPO_ROOT / "data" / "process" / "rfp"
CHECKPOINT_PATH = CHECKPOINT_DIR / "langgraph_checkpoints.db"

MAX_APPROVAL_ROUNDS = 3
VALID_DECISIONS = frozenset({"approved", "rejected", "request_changes"})


def merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(left or {})
    out.update(right or {})
    return out


def merge_lists(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    return list(left or []) + list(right or [])


def last_value(left: Any, right: Any) -> Any:
    """Last-write-wins for scalars touched by parallel branches."""
    return right if right is not None else left


class ApprovalGraphState(TypedDict, total=False):
    ticket_id: str
    metadata: dict[str, Any]
    sections: Annotated[dict[str, Any], merge_dicts]
    approvals: Annotated[dict[str, Any], merge_dicts]
    conflicts: list[dict[str, Any]]
    force_request_changes: dict[str, str]
    blocking_phi: bool
    synthesizer_blocked: bool
    # Parallel HITL nodes append via reducer (input/output/ts per node).
    trace_events: Annotated[list[dict[str, Any]], operator.add]
    final_document: dict[str, Any] | None
    status: Annotated[str, last_value]
    sales_flags: Annotated[list[dict[str, Any]], merge_lists]


def thread_id_for(ticket_id: str, department_id: str | None = None) -> str:
    """Namespace checkpoints by ticket (and optionally department).

    Concurrent tickets must never share a checkpoint thread.
    """
    base = f"rfp-{ticket_id}"
    if department_id:
        return f"{base}:{department_id}"
    return base


def validate_approval_decision(
    *,
    department_id: str,
    decision: str,
) -> str:
    """Validate the human response before it re-enters the graph."""
    dept = str(department_id or "").strip().lower()
    if dept not in KNOWN_DEPARTMENTS:
        raise ValueError(
            f"Invalid department_id={department_id!r}; "
            f"expected one of {list(KNOWN_DEPARTMENTS)}"
        )
    normalized = str(decision or "").strip().lower()
    if normalized not in VALID_DECISIONS:
        raise ValueError(
            f"Invalid decision={decision!r}; "
            f"expected one of {sorted(VALID_DECISIONS)}"
        )
    return normalized


def _ensure_checkpoint_dir() -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_PATH


def open_checkpointer() -> tuple[SqliteSaver, sqlite3.Connection]:
    path = _ensure_checkpoint_dir()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver, conn


def _default_approval(dept_id: str) -> dict[str, Any]:
    return {
        "department_id": dept_id,
        "approval_status": "pending",
        "approver": None,
        "approved_at": None,
        "approval_round": 0,
        "note": None,
    }


def _auto_guardrails(state: ApprovalGraphState) -> dict[str, Any]:
    """Schema / PHI / BAA-DPA string checks without human interrupt."""
    node_input = {
        "sections_keys": list((state.get("sections") or {}).keys()),
        "client_country": (state.get("metadata") or {}).get("client_country"),
    }
    sections = {k: dict(v) for k, v in (state.get("sections") or {}).items()}
    metadata = dict(state.get("metadata") or {})
    force: dict[str, str] = {}
    notes: list[str] = []

    for dept_id in KNOWN_DEPARTMENTS:
        section = sections.get(dept_id) or {
            "department_id": dept_id,
            "draft_content": "",
            "evaluation_results": {},
        }
        sections[dept_id] = section
        draft = str(section.get("draft_content") or "").strip()
        if not draft:
            force[dept_id] = "request_changes"
            notes.append(f"{dept_id}: empty draft")
        evals = dict(section.get("evaluation_results") or {})
        if bool(section.get("contains_phi") or evals.get("contains_phi")):
            force[dept_id] = "request_changes"
            notes.append(f"{dept_id}: PHI flag")

    country = (metadata.get("client_country") or "").upper()
    currency = currency_for_country(country or None)
    compliance_text = str((sections.get("compliance") or {}).get("draft_content") or "")
    if country == "US":
        if "baa" not in compliance_text.lower() and "business associate" not in compliance_text.lower():
            force["compliance"] = "request_changes"
            notes.append("guardrail: US missing BAA wording")
    elif country == "UK":
        if (
            "dpa" not in compliance_text.lower()
            and "data processing" not in compliance_text.lower()
            and "uk gdpr" not in compliance_text.lower()
        ):
            force["compliance"] = "request_changes"
            notes.append("guardrail: UK missing DPA wording")

    node_output = {"force_request_changes": force, "notes": notes, "currency": currency}
    return {
        "sections": sections,
        "force_request_changes": force,
        "status": "waiting_for_approval",
        "trace_events": [
            make_trace_event(
                agent="auto_guardrails",
                action="checked",
                input=node_input,
                output=node_output,
                detail=node_output,
            )
        ],
    }


def _arbitration_node(state: ApprovalGraphState) -> dict[str, Any]:
    node_input = {
        "metadata": {
            "client_country": (state.get("metadata") or {}).get("client_country"),
            "covered_population": (state.get("metadata") or {}).get("covered_population"),
            "contains_phi": (state.get("metadata") or {}).get("contains_phi"),
        },
        "section_phi": {
            dept_id: bool(
                (section or {}).get("contains_phi")
                or ((section or {}).get("evaluation_results") or {}).get("contains_phi")
            )
            for dept_id, section in (state.get("sections") or {}).items()
        },
    }
    result = apply_arbitration(
        metadata=dict(state.get("metadata") or {}),
        sections=dict(state.get("sections") or {}),
    )
    force = dict(state.get("force_request_changes") or {})
    force.update(result.get("force_request_changes") or {})

    approvals = dict(state.get("approvals") or {})
    arbiter_by_dept: dict[str, str] = {}
    for conflict in result.get("conflicts") or []:
        arbiter_name = str(conflict.get("arbiter") or "")
        for target in conflict.get("force_request_changes_departments") or []:
            arbiter_by_dept[str(target)] = arbiter_name

    for dept_id in KNOWN_DEPARTMENTS:
        current = dict(approvals.get(dept_id) or _default_approval(dept_id))
        if force.get(dept_id) == "request_changes" and current.get("approval_status") in {
            None,
            "pending",
        }:
            current["approval_status"] = "request_changes"
            current["approver"] = arbiter_by_dept.get(
                dept_id, DEPARTMENT_OWNERS.get(dept_id)
            )
        approvals[dept_id] = current

    node_output = {
        "conflicts": result.get("conflicts") or [],
        "blocking_phi": bool(result.get("blocking_phi")),
        "force_request_changes": force,
    }
    return {
        "conflicts": result.get("conflicts") or [],
        "force_request_changes": force,
        "blocking_phi": bool(result.get("blocking_phi")),
        "synthesizer_blocked": bool(result.get("synthesizer_blocked")),
        "approvals": approvals,
        "status": "waiting_for_approval",
        "trace_events": [
            make_trace_event(
                agent="arbitration",
                action="resolved_triggers",
                input=node_input,
                output=node_output,
                detail=node_output,
            )
        ],
    }


def _approval_package(state: ApprovalGraphState, dept_id: str) -> dict[str, Any]:
    """Minimum package a human needs at the interrupt (no full-doc re-read)."""
    section = dict((state.get("sections") or {}).get(dept_id) or {})
    draft = str(section.get("draft_content") or "")
    preview = draft if len(draft) <= 1200 else draft[:1200] + "\n…[truncated]"
    return {
        "type": "department_approval",
        "department_id": dept_id,
        "owner": DEPARTMENT_OWNERS[dept_id],
        "draft_preview": preview,
        "evaluation_results": dict(section.get("evaluation_results") or {}),
        "contains_phi": bool(
            section.get("contains_phi")
            or (section.get("evaluation_results") or {}).get("contains_phi")
        ),
        "key_aspects": list(section.get("key_aspects") or [])[:12],
        "open_questions": list(section.get("open_questions") or [])[:8],
        "conflicts": [
            c
            for c in (state.get("conflicts") or [])
            if dept_id in (c.get("force_request_changes_departments") or [])
            or c.get("arbiter_department_id") == dept_id
            or c.get("trigger_id") == "phi-detected"
        ],
        "approval_round": int(
            ((state.get("approvals") or {}).get(dept_id) or {}).get("approval_round") or 0
        ),
        "max_rounds": MAX_APPROVAL_ROUNDS,
        "client_country": (state.get("metadata") or {}).get("client_country"),
        "client_name": (state.get("metadata") or {}).get("client_name"),
    }


def _apply_human_decision(
    *,
    dept_id: str,
    current: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Apply validated HITL decision. Returns (approval, optional sales_flag)."""
    decision = validate_approval_decision(
        department_id=dept_id,
        decision=str(payload.get("decision") or ""),
    )
    # Resume payload may target another department — reject before mutating.
    payload_dept = str(payload.get("department_id") or dept_id).strip().lower()
    if payload_dept != dept_id:
        raise ValueError(
            f"Resume payload department_id={payload_dept!r} does not match "
            f"interrupted branch {dept_id!r}"
        )

    owner = DEPARTMENT_OWNERS[dept_id]
    round_n = int(current.get("approval_round") or 0)
    note = payload.get("note")
    actor = payload.get("actor")
    sales_flag: dict[str, Any] | None = None
    updated = dict(current)

    if decision in {"rejected", "request_changes"}:
        round_n += 1
        updated.update(
            {
                "approval_round": round_n,
                "approval_status": decision,
                "approver": owner,
                "approved_at": None,
                "note": note,
                "actor_email": actor,
            }
        )
        if round_n >= MAX_APPROVAL_ROUNDS:
            sales_flag = {
                "department_id": dept_id,
                "reason": "approval_round_limit",
                "rounds": round_n,
                "last_decision": decision,
                "requires_part2_redraft": True,
            }
    else:
        updated.update(
            {
                "approval_status": "approved",
                "approver": owner,
                "approved_at": payload.get("approved_at"),
                "note": note,
                "actor_email": actor,
                "approval_round": round_n,
            }
        )
    return updated, sales_flag


def _make_hitl_node(dept_id: str):
    """Factory: one interrupt branch per department (independent pause)."""

    def _hitl(state: ApprovalGraphState) -> dict[str, Any]:
        approvals_in = dict(state.get("approvals") or {})
        current = dict(approvals_in.get(dept_id) or _default_approval(dept_id))
        traces: list[dict[str, Any]] = []
        sales_flags: list[dict[str, Any]] = []

        # Already approved (e.g. resumed earlier on this branch).
        if current.get("approval_status") == "approved":
            traces.append(
                make_trace_event(
                    agent=f"hitl_{dept_id}",
                    action="skip_already_approved",
                    department_id=dept_id,
                    input={"approval_status": current.get("approval_status")},
                    output={"skipped": True},
                )
            )
            return {
                "approvals": {dept_id: current},
                "trace_events": traces,
            }

        # Round-limit exhausted → leave flagged for Sales (no more interrupts).
        if int(current.get("approval_round") or 0) >= MAX_APPROVAL_ROUNDS and current.get(
            "approval_status"
        ) in {"rejected", "request_changes"}:
            traces.append(
                make_trace_event(
                    agent=f"hitl_{dept_id}",
                    action="approval_limit_reached",
                    department_id=dept_id,
                    input={"approval_round": current.get("approval_round")},
                    output={"terminal": current.get("approval_status")},
                )
            )
            return {
                "approvals": {dept_id: current},
                "trace_events": traces,
                "sales_flags": [
                    {
                        "department_id": dept_id,
                        "reason": "approval_round_limit",
                        "rounds": current.get("approval_round"),
                        "last_decision": current.get("approval_status"),
                        "requires_part2_redraft": True,
                    }
                ],
            }

        while True:
            package = _approval_package(state, dept_id)
            package["current_approval"] = current
            traces.append(
                make_trace_event(
                    agent=f"hitl_{dept_id}",
                    action="interrupt",
                    department_id=dept_id,
                    input={
                        "owner": package["owner"],
                        "approval_round": package["approval_round"],
                        "contains_phi": package["contains_phi"],
                    },
                    output={"awaiting": "human_decision"},
                )
            )
            payload = interrupt(package)
            if not isinstance(payload, dict):
                raise ValueError("HITL resume payload must be a dict")

            updated, sales_flag = _apply_human_decision(
                dept_id=dept_id,
                current=current,
                payload=payload,
            )
            current = updated
            traces.append(
                make_trace_event(
                    agent=f"hitl_{dept_id}",
                    action=str(updated.get("approval_status")),
                    department_id=dept_id,
                    input={
                        "decision": payload.get("decision"),
                        "actor": payload.get("actor"),
                        "note": payload.get("note"),
                    },
                    output=updated,
                    detail={
                        "owner": DEPARTMENT_OWNERS[dept_id],
                        "round": updated.get("approval_round"),
                    },
                )
            )
            if sales_flag:
                sales_flags.append(sales_flag)
                traces.append(
                    make_trace_event(
                        agent=f"hitl_{dept_id}",
                        action="approval_limit_reached",
                        department_id=dept_id,
                        input={"rounds": sales_flag.get("rounds")},
                        output=sales_flag,
                    )
                )
                break

            if updated.get("approval_status") == "approved":
                break

            # reject / request_changes: loop for another interrupt on THIS branch only.
            # Content regeneration is NOT automatic — Sales must re-run Part 2 drafting
            # explicitly when requires_part2_redraft or after reviewing the note.

        # Do not write `status` here — parallel HITL completions would collide.
        return {
            "approvals": {dept_id: current},
            "trace_events": traces,
            "sales_flags": sales_flags,
        }

    _hitl.__name__ = f"hitl_{dept_id}"
    return _hitl


def _pending_departments(approvals: dict[str, dict[str, Any]]) -> list[str]:
    pending: list[str] = []
    for dept_id in KNOWN_DEPARTMENTS:
        status = (approvals.get(dept_id) or {}).get("approval_status")
        if status != "approved":
            pending.append(dept_id)
    return pending


def _join_and_synthesize(state: ApprovalGraphState) -> dict[str, Any]:
    node_input = {
        "approvals": {
            d: (state.get("approvals") or {}).get(d, {}).get("approval_status")
            for d in KNOWN_DEPARTMENTS
        },
        "blocking_phi": bool(state.get("blocking_phi")),
    }
    traces: list[dict[str, Any]] = []

    if state.get("blocking_phi") or state.get("synthesizer_blocked"):
        out = {
            "final_document": None,
            "status": "waiting_for_approval",
            "synthesizer_blocked": True,
        }
        traces.append(
            make_trace_event(
                agent="join_synthesize",
                action="blocked_phi",
                input=node_input,
                output=out,
                detail="Synthesizer refused: PHI still blocking",
            )
        )
        return {**out, "trace_events": traces}

    approvals = dict(state.get("approvals") or {})
    pending = _pending_departments(approvals)
    if pending:
        out = {
            "final_document": None,
            "status": "waiting_for_approval",
        }
        traces.append(
            make_trace_event(
                agent="join_synthesize",
                action="incomplete",
                input=node_input,
                output={"pending": pending},
            )
        )
        return {**out, "trace_events": traces}

    # Mirror approval fields onto sections for the synthesizer.
    sections = {k: dict(v) for k, v in (state.get("sections") or {}).items()}
    for dept_id, approval in approvals.items():
        section = dict(sections.get(dept_id) or {"department_id": dept_id})
        section["approval_status"] = approval.get("approval_status")
        section["approver"] = approval.get("approver")
        section["approved_at"] = approval.get("approved_at")
        section["approval_round"] = approval.get("approval_round", 0)
        sections[dept_id] = section

    try:
        final_doc = synthesize_final_document(
            ticket_id=str(state.get("ticket_id") or ""),
            metadata=dict(state.get("metadata") or {}),
            sections=sections,
            approvals=approvals,
        )
    except FinalDocumentError as exc:
        out = {
            "final_document": None,
            "status": "waiting_for_approval",
            "synthesizer_blocked": True,
        }
        traces.append(
            make_trace_event(
                agent="join_synthesize",
                action="refused",
                input=node_input,
                output={"error": str(exc)},
            )
        )
        return {**out, "trace_events": traces}

    serializable = {
        **final_doc,
        "generated_at": final_doc["generated_at"].isoformat(),
    }
    out = {
        "final_document": serializable,
        "sections": sections,
        "status": "done",
        "synthesizer_blocked": False,
    }
    traces.append(
        make_trace_event(
            agent="join_synthesize",
            action="synthesized",
            input=node_input,
            output={"currency": final_doc.get("currency"), "status": "done"},
        )
    )
    return {**out, "trace_events": traces}


def build_approval_graph(checkpointer: SqliteSaver):
    graph = StateGraph(ApprovalGraphState)
    graph.add_node("auto_guardrails", _auto_guardrails)
    graph.add_node("arbitration", _arbitration_node)
    for dept_id in KNOWN_DEPARTMENTS:
        graph.add_node(f"hitl_{dept_id}", _make_hitl_node(dept_id))
    graph.add_node("join_synthesize", _join_and_synthesize)

    graph.add_edge(START, "auto_guardrails")
    graph.add_edge("auto_guardrails", "arbitration")
    for dept_id in KNOWN_DEPARTMENTS:
        graph.add_edge("arbitration", f"hitl_{dept_id}")
        graph.add_edge(f"hitl_{dept_id}", "join_synthesize")
    graph.add_edge("join_synthesize", END)
    return graph.compile(checkpointer=checkpointer)


def _config(ticket_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id_for(ticket_id)}}


def start_approval_graph(
    *,
    ticket_id: str,
    metadata: dict[str, Any],
    sections: dict[str, dict[str, Any]],
    prior_trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run until department HITL interrupts (parallel). Explicit start entrypoint."""
    checkpointer, conn = open_checkpointer()
    try:
        app = build_approval_graph(checkpointer)
        initial: ApprovalGraphState = {
            "ticket_id": ticket_id,
            "metadata": metadata,
            "sections": sections,
            "approvals": {},
            "conflicts": [],
            "force_request_changes": {},
            "blocking_phi": False,
            "synthesizer_blocked": False,
            "trace_events": list(prior_trace or []),
            "final_document": None,
            "status": "waiting_for_approval",
            "sales_flags": [],
        }
        result = app.invoke(initial, config=_config(ticket_id))
        snap = app.get_state(_config(ticket_id))
        return _pack_result(result, snap)
    finally:
        conn.close()


def _interrupt_resume_map(snap: Any, department_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Map resume value to the interrupt id of the target department branch only."""
    resume_map: dict[str, Any] = {}
    for task in getattr(snap, "tasks", None) or []:
        for item in getattr(task, "interrupts", None) or []:
            value = getattr(item, "value", None)
            if isinstance(value, dict) and value.get("department_id") == department_id:
                resume_map[str(item.id)] = payload
    return resume_map


def resume_approval_graph(
    *,
    ticket_id: str,
    department_id: str,
    decision: str,
    actor: str | None = None,
    note: str | None = None,
    approved_at: str | None = None,
) -> dict[str, Any]:
    """Explicit resume entrypoint — does not restart the whole flow.

    Validates the human response, then resumes only that department's interrupt.
    """
    decision_n = validate_approval_decision(
        department_id=department_id, decision=decision
    )
    payload = {
        "department_id": department_id,
        "decision": decision_n,
        "actor": actor,
        "note": note,
        "approved_at": approved_at,
    }
    checkpointer, conn = open_checkpointer()
    try:
        app = build_approval_graph(checkpointer)
        cfg = _config(ticket_id)
        snap = app.get_state(cfg)
        resume_map = _interrupt_resume_map(snap, department_id, payload)
        if not resume_map:
            pending = [
                (getattr(i, "value", None) or {}).get("department_id")
                for t in (getattr(snap, "tasks", None) or [])
                for i in (getattr(t, "interrupts", None) or [])
            ]
            raise ValueError(
                f"No open interrupt for department_id={department_id!r}; "
                f"pending={pending}; next={list(getattr(snap, 'next', None) or [])}"
            )
        result = app.invoke(Command(resume=resume_map), config=cfg)
        snap2 = app.get_state(cfg)
        return _pack_result(result, snap2)
    finally:
        conn.close()


def _approvals_from_interrupts(snap: Any) -> dict[str, dict[str, Any]]:
    """Merge in-flight interrupt packages + committed state for UI/persistence."""
    committed = dict((getattr(snap, "values", None) or {}).get("approvals") or {})
    for task in getattr(snap, "tasks", None) or []:
        for item in getattr(task, "interrupts", None) or []:
            value = getattr(item, "value", None)
            if not isinstance(value, dict):
                continue
            dept = value.get("department_id")
            if not dept:
                continue
            current = value.get("current_approval")
            if isinstance(current, dict):
                committed[str(dept)] = dict(current)
            else:
                committed.setdefault(str(dept), _default_approval(str(dept)))
    return committed


def _pack_result(result: dict[str, Any] | Any, snap: Any) -> dict[str, Any]:
    values = dict(result or {}) if isinstance(result, dict) else {}
    if snap is not None and getattr(snap, "values", None):
        merged = dict(snap.values)
        # Prefer reducer-committed values; overlay non-None invoke results.
        for key, val in values.items():
            if val is not None and key not in {"trace_events"}:
                merged[key] = val
        # trace_events: use snap (full history via reducer)
        values = merged

    interrupted = bool(getattr(snap, "next", None))
    live_approvals = _approvals_from_interrupts(snap) if snap is not None else {}
    if live_approvals:
        values["approvals"] = live_approvals

    pending_depts = [
        (getattr(i, "value", None) or {}).get("department_id")
        for t in (getattr(snap, "tasks", None) or [])
        for i in (getattr(t, "interrupts", None) or [])
    ]

    return {
        "status": values.get("status")
        or ("waiting_for_approval" if interrupted else "done"),
        "approvals": values.get("approvals") or {},
        "conflicts": values.get("conflicts") or [],
        "blocking_phi": bool(values.get("blocking_phi")),
        "synthesizer_blocked": bool(values.get("synthesizer_blocked")),
        "trace_events": values.get("trace_events") or [],
        "final_document": values.get("final_document"),
        "sales_flags": values.get("sales_flags") or [],
        "sections": values.get("sections") or {},
        "interrupted": interrupted,
        "next": list(getattr(snap, "next", None) or []),
        "pending_interrupt_departments": [d for d in pending_depts if d],
        "thread_id": thread_id_for(str(values.get("ticket_id") or "")),
    }


__all__ = [
    "MAX_APPROVAL_ROUNDS",
    "VALID_DECISIONS",
    "CHECKPOINT_PATH",
    "thread_id_for",
    "validate_approval_decision",
    "start_approval_graph",
    "resume_approval_graph",
    "build_approval_graph",
    "open_checkpointer",
]
