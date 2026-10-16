# Part 2 evidence — traces + evals (PR checklist)

Generated from `run_agent()` on branch `feature/langgraph-external-tools`.
Full JSON dumps:

- Ticket tool run: [`agent-trace-ticket-tool.json`](./agent-trace-ticket-tool.json)
- RAG-only run: [`agent-trace-rag-policy.json`](./agent-trace-rag-policy.json)
- Eval console output: [`agent-evals-part2-output.txt`](./agent-evals-part2-output.txt)

## 1. Trace — agent used the **ticket tool** (not RAG)

**Question:** `What is the status of ticket 482?`

| Field | Value |
|-------|--------|
| `route` | `incidents` |
| `sources_used` | `["incidents"]` |
| Span order | `receive → decide_route → lookup_incident → answer_from_tool` |
| RAG called? | **No** (`retrieve` absent) |

```json
{
  "route": "incidents",
  "sources_used": ["incidents"],
  "answer": "Ticket 482: status=in_progress, category=it_system, origin=branch, branch=austin_north, title='Printer offline', updated_at=2026-01-11T09:30:00Z.",
  "spans": [
    {"node": "receive", "output": {"question_chars": 33}},
    {"node": "decide_route", "output": {"route": "incidents", "ticket_id": 482, "sku": null}},
    {
      "node": "lookup_incident",
      "output": {
        "source_kind": "incidents",
        "ok": true,
        "error": null,
        "n_incidents": 1,
        "ticket_id": 482
      }
    },
    {
      "node": "answer_from_tool",
      "output": {"answer_chars": 140, "source_kind": "incidents"}
    }
  ]
}
```

## 2. Trace — agent used the **RAG** (not a tool)

**Question:** `Is there a charge for cancelling 12 hours in advance?`

| Field | Value |
|-------|--------|
| `route` | `rag` |
| `sources_used` | `["rag"]` |
| Span order | `receive → decide_route → retrieve → generate` |
| Tool called? | **No** (`lookup_incident` / `lookup_inventory` absent) |

```json
{
  "route": "rag",
  "sources_used": ["rag"],
  "answer": "Yes. Cancelling less than 24 hours in advance, or a no-show, is 50 USD (or 40 GBP in the UK) for private-pay patients. Medicare/Medicaid are exempt.",
  "spans": [
    {"node": "receive", "output": {"question_chars": 53}},
    {"node": "decide_route", "output": {"route": "rag", "ticket_id": null, "sku": null}},
    {
      "node": "retrieve",
      "output": {
        "n_chunks": 1,
        "n_policy_chunks": 1,
        "sources": ["appointment-policy"],
        "source_kind": "rag",
        "hybrid": false
      }
    },
    {"node": "generate", "output": {"answer_chars": 146}}
  ]
}
```

## 3. New evals — console result

Command:

```bash
python -m pytest tests/pipelines/test_agent_evals.py -v --tb=line
```

**Result: 16 passed, 1 skipped** (`test_live_grounded_cancellation_answer` needs `RUN_LIVE_EVALS=1`).

Part 2 routing evals (new / extended):

| Test | Role |
|------|------|
| `test_eval_tool_not_rag_on_golden_trace` | Tool path, no RAG |
| `test_eval_rag_not_tool_on_golden_trace` | RAG path, no tool |
| `test_eval_tool_fallback_on_golden_trace` | Fallback when incidents unavailable |
| `test_eval_hybrid_tool_and_rag_on_golden_trace` | Both sources, tool before RAG |
| `test_generator_ticket_run_passes_tool_routing_eval` | Anti-rot tool |
| `test_generator_policy_run_passes_rag_routing_eval` | Anti-rot RAG |
| `test_generator_hybrid_run_passes_both_sources_eval` | Anti-rot hybrid |
| `test_generator_tool_failure_passes_fallback_eval` | Anti-rot fallback |

Full suite (tools + graph + evals): **54 passed, 1 skipped**.
