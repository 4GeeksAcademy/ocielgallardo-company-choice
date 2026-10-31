# RFP intake — improvement proposal (2026-10-31)

**Scope:** documentation only. No code, schema, or dependency changes are made in this PR.
**Baseline:** `main` @ `143c08d` (merge of PR #53). All file/line references below point to that commit.
**Area:** Part 1 intake (`POST /rfp/tickets` → Celery `rfp.intake_run` → LangGraph intake graph → backoffice `RfpIntakePanel`).

Reported symptoms:

1. Tickets "stay in `analyzing` forever".
2. Unreadable PDFs (scanned or corrupt) never reach a clear end state.
3. Irrelevant PDFs are not always rejected, or the rejection is not obvious.
4. The panel does not refresh live; the **Retry** button or the final state often appears only after a page reload.

Related doc: [`language-check-2026-10-31.md`](./language-check-2026-10-31.md) (docs/UI language audit, delivered in the same PR).

---

## 1. Summary

| # | Problem | Root cause (short) | Proposed fix | Effort |
|---|---------|--------------------|--------------|--------|
| A | Unreadable PDF stays `analyzing` | Errors only write `last_error`; `status` is never moved to a terminal value; Celery retries deterministic failures 3× | New terminal status `failed` + user-facing `failure_reason`; classify errors as permanent vs transient; no auto-retry for permanent errors | **M** (~1 day) |
| B | Non-PDF / text renamed `.pdf` is accepted | Upload only checks the extension and Content-Type; MarkItDown falls back to plain-text conversion | Check `%PDF-` magic bytes in the router (400) and minimum-text guard in `convert` | **S** (~2 h) |
| C | Irrelevant PDFs pass the classifier | Heuristic treats any "RFP / request for proposal" wording as a HealthCore RFP, without checking domain relevance; LLM is called even when the heuristic is confident | Add a domain-relevance gate (healthcare / occupational health / wellness / referral) to the heuristic, short-circuit confident heuristic results before any paid LLM call, rename discard copy for users | **S–M** (~0.5 day) |
| D | No live refresh / Retry only after reload | Polling `useEffect` depends only on `selectedId`; actions (Retry, Start/Retry drafting, Start approvals) never restart it; a fetch error stops polling; ticket list never refreshes while items are non-terminal | Restart polling on every action (poll "generation" counter), keep polling while any status is non-terminal, back off on errors instead of stopping; SSE status events as a follow-up | **S–M** (~0.5 day) |
| E | No guard for silent hangs | Worker crash / never-consumed message / hard time limit leaves `analyzing` with no `last_error`; Retry is refused in that state | Stale-ticket guard (Celery beat sweeper + on-read check) that marks `failed` after N minutes without progress; allow Retry on stale tickets | **M** (~1 day) |
| F | Live status via SSE | PR #52 (SSE) is **not on `main`** and only emits `rfp_ticket_created` | Land SSE on `main`, then add `rfp_ticket_status_changed` events from every status transition | **M** (~1 day, after D) |

**Migration:** not required. `RfpTicket.status` is `varchar(64)`, not a Postgres enum (`services/app/models/rfp.py`, `status: str = Field(default="analyzing", max_length=64, index=True)`). New values (`failed`) can be written without DDL. A nullable `failure_reason` column is optional: the proposal below can reuse `last_error` (technical) + `discard_reason` (user-facing) without schema changes; adding a dedicated column would need one small additive Alembic migration.

---

## 2. Current flow (for reference)

```
POST /rfp/tickets                       services/app/routers/rfp.py:52-105
  ├─ validate extension / content-type / size (no magic-byte check)   :62-77
  ├─ create ticket status="analyzing"   services/app/domain/rfp_service.py:57
  └─ run_rfp_intake_task.apply_async    :88-99 (enqueue failure → set_ticket_error only)

Celery rfp.intake_run                   services/app/tasks/rfp_intake.py:31-63
  └─ run_rfp_intake(ticket_id)          data/pipelines/rfp_intake/__init__.py:13-100
       └─ run_intake_graph → graph.invoke
            convert_node   (MarkItDown)          data/pipelines/rfp_intake/graph.py:33
            classify_node  (heuristic + LLM)     graph.py:54
            ├─ discard_node → status "discarded" graph.py:70
            └─ orchestrate → workers_parallel (ThreadPoolExecutor, graph.py:108) → synthesize
       success → status "intake_complete", last_error=None   __init__.py:91-94
       discarded → status "discarded", discard_reason          __init__.py:33-46
       exception → set_ticket_error(str(exc)) and re-raise     __init__.py:26-30

UI: uis/backoffice/components/rfp/RfpIntakePanel.tsx
  polling effect :320-362   |   intake error box :630-646   |   discarded copy :137-143, :675-679
```

Status values in use: `analyzing`, `discarded`, `intake_complete`, `drafting`, `under_evaluation`, `needs_human_review`, `waiting_for_approval`, `done`. There is **no terminal failure status**: failure is encoded as `status="analyzing" AND last_error IS NOT NULL` (see `derive_pipeline_stage`, `rfp_service.py:237-268`, which returns `("failed", True)` at line 263).

---

## 3. Findings and proposals

### A. Unreadable PDF never reaches a terminal state

**Root cause**

- `data/pipelines/rfp_intake/convert.py:16-19` — a PDF without a text layer (scanned image, blank pages) raises `ValueError("MarkItDown produced empty Markdown for the uploaded PDF")`. A malformed PDF raises whatever exception MarkItDown/pdfminer throws.
- `data/pipelines/rfp_intake/__init__.py:26-30` and again `services/app/tasks/rfp_intake.py:47-50` both call `rfp_service.set_ticket_error(...)` with `str(exc)`. `set_ticket_error` (`rfp_service.py:513-518`) writes only `last_error` and `updated_at`; **`status` stays `analyzing`**.
- `services/app/tasks/rfp_intake.py:61-62` retries **every** exception up to `MAX_RETRIES = 3` (line 17) with backoff `2**retries` seconds — including deterministic failures (empty text, corrupt file, missing file). The same failure is repeated 4 times and, between attempts, `last_error` is already set, so the UI shows **Retry intake** while Celery is still auto-retrying. A manual retry during that window (`prepare_ticket_retry`, `rfp_service.py:483-510`) enqueues a **second concurrent run** for the same ticket.
- `RfpIntakePanel.tsx:630-646` shows the raw exception: `Intake error (status remains analyzing until retry succeeds): {detail.last_error}`. It does not pass the text through `friendlyRfpLastError` (`uis/backoffice/lib/services/rfpApi.ts:231-252`), and that helper has no intake-specific mappings anyway.
- In the ticket list, `RfpTicketSummary` (`services/app/schemas.py:257-265`) has no `last_error` field, so a failed ticket is rendered with the amber **Analyzing** badge (`statusLabel` / `statusClass`, `RfpIntakePanel.tsx:41-87`). From the list view, failed tickets are indistinguishable from running ones — this is the main "stuck in analyzing" perception.

Verified locally (2026-10-31, project venv): a structurally valid PDF with one blank page → `ValueError: MarkItDown produced empty Markdown for the uploaded PDF`.

**Proposed change**

1. Add a small exception hierarchy in `data/pipelines/rfp_intake/errors.py`:
   - `RfpIntakePermanentError(user_message: str, code: str)` — not retryable.
   - Subclasses: `PdfUnreadableError` (`code="pdf_unreadable"`, "We could not read any text in this PDF. It may be a scanned image or password-protected. Upload a text-based PDF."), `PdfCorruptError` (`code="pdf_corrupt"`, "This file is not a valid PDF or is damaged."), `PdfMissingError` (`code="pdf_missing"`).
2. `convert.py`: raise `PdfUnreadableError` for empty text or text below a minimum (for example `< 200` non-whitespace characters, configurable via `RFP_MIN_TEXT_CHARS`); wrap MarkItDown exceptions in `PdfCorruptError`; replace `FileNotFoundError` with `PdfMissingError`.
3. New service function `rfp_service.mark_ticket_failed(session, ticket_id, *, code, user_message, technical)`: sets `status="failed"`, `last_error=technical[:4000]`, `discard_reason=user_message` (or a new `failure_reason` column, see Migration), `updated_at=now`.
4. `tasks/rfp_intake.py`: `except RfpIntakePermanentError` → `mark_ticket_failed` and **return without `self.retry`**. Other exceptions are treated as transient: keep `set_ticket_error` + retry, and on the **last** attempt call `mark_ticket_failed(code="pipeline_error", user_message="The analysis failed after several attempts. Use Retry to run it again.")`.
5. Remove the duplicated `set_ticket_error` in `__init__.py:26-30` (the task is the single owner of error persistence) — keeps behaviour deterministic for tests.
6. `derive_pipeline_stage`: `status == "failed"` → `("failed", True)`. `prepare_ticket_retry`: accept `status in {"failed"}` or (`analyzing` + `last_error`) for backward compatibility; reset to `analyzing`.
7. Backoffice: add `failed` to `statusLabel` ("Failed"), `statusClass` (red), `RfpTicketStatus` union in `rfpApi.ts:8-17` (`RfpPipelineStage` already includes `failed`); show `discard_reason`/`failure_reason` as the main message and the raw `last_error` only in a collapsible "Technical details" element. Replace the copy "status remains analyzing until retry succeeds".
8. Optionally expose `last_error_present: bool` (or the new status) in `RfpTicketSummary` so the list badge is correct even for legacy rows.

**Tests to add**

- `tests/pipelines/test_rfp_convert.py`
  - blank-page PDF → `PdfUnreadableError` (fixture generated inline as bytes; no new dependency).
  - non-PDF bytes → `PdfCorruptError`.
  - tiny text below threshold → `PdfUnreadableError`.
- `tests/test_rfp_intake_task.py` (Celery eager mode or calling `run_rfp_intake_task.run` with a mocked `self.retry`)
  - permanent error → ticket `status == "failed"`, `self.retry` **not** called.
  - transient error on last attempt → `failed` with generic user message.
  - transient error on first attempt → `retry` called, status still `analyzing`.
- `tests/test_rfp_service.py`
  - `derive_pipeline_stage(status="failed", ...) == ("failed", True)`.
  - `prepare_ticket_retry` accepts `failed`, still rejects `discarded` / `intake_complete`.

**Effort:** M (≈1 day including UI copy and tests).

---

### B. Non-PDF content is accepted as a PDF

**Root cause**

- `services/app/routers/rfp.py:62-77` validates only the filename extension, the declared Content-Type (which includes the generic `application/octet-stream`), emptiness and size. There is no `%PDF-` magic-byte check.
- MarkItDown selects a converter by content; for a file named `.pdf` that is really text it falls back to the plain-text converter. Verified locally: bytes `"this is not a pdf at all"` saved as `corrupt.pdf` → converted "successfully" to Markdown and passed on to the classifier.

**Proposed change**

- Router: reject with `400 "The file is not a valid PDF."` when `not pdf_bytes.startswith(b"%PDF-")` (allow leading whitespace/BOM up to 1 KB as the PDF spec permits).
- Defence in depth in `convert.py`: same check before calling MarkItDown → `PdfCorruptError` (covers files placed by scripts/seeds).

**Tests to add**

- `tests/test_rfp_upload.py`: upload `b"hello"` with filename `x.pdf` → 400 and no ticket row created; valid header → 202/201 (Celery mocked).

**Effort:** S (≈2 h).

---

### C. Irrelevant PDFs are not reliably rejected

**Root cause**

- `data/pipelines/rfp_intake/classifier.py:11-18` (`_RFP_POSITIVE`) accepts generic procurement wording (`request for proposal`, `rfp`, `proposal request`, `seeking a partner`). Lines 62-67 return `is_rfp=True` for **any** hit, with confidence `0.55 + 0.1 × hits`. There is no check that the request is about HealthCore's services.
- Lines 69-74 accept any document mentioning `partnership`, `satellite clinic` or `referral` (confidence 0.7), so newsletters or vendor mails with "referral program" are treated as RFPs.
- Verified locally with `classify_rfp_heuristic`:
  - "Request for Proposal: resurfacing of County Road 12, asphalt paving…" → `is_rfp=True, confidence=0.65`.
  - "RFP: catering services for the annual company picnic." → `is_rfp=True, confidence=0.65`.
  - "Quarterly newsletter: our bakery opens a new store downtown." → `is_rfp=False` (correct).
- `classify_rfp` (`classifier.py:82-110`) **always** calls `chat_json` when an LLM is configured, even when the heuristic is confident. The heuristic only wins on conflicts at `confidence >= 0.85`. So every irrelevant PDF costs one paid LLM call, and the result depends on LLM availability (`RFP_LLM_TIMEOUT_SEC`).
- The discard path itself works (`graph.py:54-75` → `__init__.py:33-46` sets `status="discarded"` + `discard_reason`), but the UI copy is technical: "Pipeline stopped at classifier (document discarded)." (`RfpIntakePanel.tsx:140`) and "Discarded: {reason}" (`:677`).

**Proposed change**

1. Add `_DOMAIN_POSITIVE` (healthcare / clinic / occupational health / wellness / employee health / screening / vaccination / urgent care / referral network / patients / covered lives) to the heuristic. Rule: `rfp_hits > 0 and domain_hits == 0` → `is_rfp=False`, reason "This looks like a request for proposal outside HealthCore's services (no healthcare scope found).", confidence 0.85.
2. Tighten the informal fallback (lines 69-74): require a domain hit plus a request verb (`would like`, `looking for`, `interested in`).
3. Short-circuit in `classify_rfp`: if the heuristic returns `confidence >= 0.85` (either way), **return it without calling the LLM**. This satisfies "no paid LLM for irrelevant PDFs" for the clear cases; only ambiguous documents (0.6–0.8) reach the LLM.
4. Keep the existing terminal status `discarded` (no new `rejected` value needed — it already is the terminal "not relevant" state, and `prepare_ticket_retry` refuses it). UI copy: label "Not a relevant RFP", message "This document was not processed because it does not look like a HealthCore RFP: {reason}. Upload a different file if this is a mistake."

**Tests to add** (extend `tests/pipelines/test_rfp_classifier.py`)

- Road-paving RFP and catering RFP → `is_rfp=False`, `confidence >= 0.85`.
- Existing positive fixtures (occupational health, corporate wellness, referral network) still pass.
- `classify_rfp` with `chat_json` mocked: not called when the heuristic is confident (`assert mock.call_count == 0`); called for an ambiguous document.
- Graph-level: irrelevant Markdown → final state `status == "discarded"` and no department workers invoked.

**Effort:** S–M (≈0.5 day; most time goes to fixture review so real RFPs are not rejected).

---

### D. No live refresh; Retry / final state only after reload

**Root cause** (`uis/backoffice/components/rfp/RfpIntakePanel.tsx`)

- The polling effect (`:320-362`) has dependencies `[selectedId, loadDetail, refreshList]` (`:362`). It only (re)starts when the selected ticket changes.
- When the ticket is not running (has `last_error`, is `intake_complete`, `discarded`, etc.), the loop stops (`:337-351`). After the user clicks **Retry intake** (`onRetry`, `:380-395`), **Retry drafting** (`onRetryDraft`), **Start drafting** (`onStartDraft`) or **Start approvals** (`onStartApproval`), the handlers call `loadDetail` **once** and never restart the loop, because `selectedId` did not change. The ticket then looks frozen until the user reloads or re-selects it.
- On a fetch error the `catch` block (`:352-356`) sets an error and **does not reschedule** the next tick — one transient 5xx/network error permanently stops refresh.
- The ticket list (`refreshList`) is loaded once on mount (`:314-318`) and after actions; other tickets in `analyzing` never update their badges.
- `pollSlow` copy (`:621-626`) says "use **Retry drafting**" even during intake, where that button is not shown; during a silent hang (see E) there is no actionable button at all.
- After 90 s the loop keeps polling every 2.5 s indefinitely (no backoff, no upper bound).

**Proposed change**

1. Introduce `const [pollGen, setPollGen] = useState(0)` and add it to the effect dependencies; call `setPollGen((g) => g + 1)` at the end of every action handler (retry, start/retry draft, start approval, decide). This restarts the loop deterministically.
2. Compute `running` from a single `isNonTerminal(status, last_error)` helper shared with the list: terminal = `intake_complete | discarded | failed | needs_human_review | done | draft_ready` (or any status with `last_error`).
3. On fetch errors, reschedule with exponential backoff (2.5 s → 5 s → 10 s, cap 30 s) instead of stopping; show a small "Reconnecting…" hint.
4. After 90 s slow down to 10 s; after 15 min stop and show "Still running after 15 minutes — Retry" (ties into guard E).
5. List: poll `listRfpTickets()` every 10 s while any row is non-terminal; stop when none is.
6. Fix the slow-path copy to name the correct action per phase (intake → **Retry intake**, drafting → **Retry drafting**).

**Tests to add**

- The backoffice currently has no component test runner configured; adding one would be a new dependency, so as part of this proposal the logic should be extracted into a pure helper `lib/rfp/polling.ts` (`isNonTerminal`, `nextDelayMs(attempt, elapsedMs, failed)`), type-checked by `tsc` and unit-tested with Node's built-in `node:test` runner (no new deps).
- Manual QA script (documented in the PR): upload a blank PDF → panel shows **Failed** + Retry within 10 s without reload; click Retry → panel returns to running and then to Failed again without reload.

**Effort:** S–M (≈0.5 day).

---

### E. No guard against silent hangs

**Root cause**

- `services/app/tasks/celery_app.py:31-36` sets `task_acks_late=True`, `task_reject_on_worker_lost=True`, `task_soft_time_limit=900`, `task_time_limit=960`, and `visibility_timeout=3600`. Behaviour by case:
  - **Soft limit (900 s)** raises `SoftTimeLimitExceeded` (an `Exception`) inside the task → handled by the generic `except` → `last_error` set and **retried** up to 3 times. Worst case is about 4 × 15 min ≈ 1 h of "analyzing".
  - **Hard limit (960 s), OOM, or worker kill:** no Python handler runs. With `reject_on_worker_lost` the message is re-queued and may loop. `last_error` stays `NULL`.
  - **Broker accepted the message but no worker is running:** `apply_async` succeeds (`routers/rfp.py:88-93`), so no error is recorded and the ticket stays `analyzing` with no `last_error` forever.
- In all `last_error IS NULL` cases:
  - `derive_pipeline_stage` reports `converting/agents/synthesizing` (not failed).
  - `prepare_ticket_retry` refuses the retry (`rfp_service.py:498-502`, "Pipeline is still running…").
  - The UI polls forever. **There is no way out except DB surgery.** This is the "stuck forever" case.
- `graph.py:108-111` runs department workers in a `ThreadPoolExecutor` and waits on `fut.result()` with no per-future timeout. One slow LLM call (each limited only by `RFP_LLM_TIMEOUT_SEC`, but called many times) can push the whole run to the soft limit.
- No code compares `updated_at` with "now" for tickets.

**Proposed change**

1. Constants in `rfp_service`: `INTAKE_STALE_AFTER = timedelta(minutes=int(os.getenv("RFP_INTAKE_STALE_MIN", "20")))`.
2. `rfp_service.is_stale(ticket, now)`: true when `status == "analyzing"`, `last_error IS NULL` and `updated_at < now - INTAKE_STALE_AFTER`.
3. On-read guard: in `GET /rfp/tickets/{id}` and the list, mark stale tickets with `mark_ticket_failed(code="pipeline_timeout", user_message="The analysis did not finish in time. Use Retry to run it again.")`. This is idempotent and needs no new infrastructure.
4. Optional periodic sweeper: a Celery beat task `rfp.sweep_stale_intake` every 5 min doing the same in bulk (only if beat is already deployed; otherwise the on-read guard is enough).
5. Per-stage progress: touch `updated_at` at the end of each graph node (`convert`, `classify`, each worker), so "stale" means "no progress", not "long document".
6. `graph.py:108-111`: `as_completed(futures, timeout=RFP_WORKERS_TIMEOUT_SEC)` (default 600 s). On `TimeoutError` raise a transient error so the task logic in A applies.
7. Task-level: in `run_rfp_intake_task`, catch `SoftTimeLimitExceeded` explicitly → `mark_ticket_failed(code="pipeline_timeout")` **without retry** (a retry is very likely to time out again).
8. Idempotency: store `celery_task_id` on the ticket (already returned by the router) and have the task exit early if the ticket is not in `analyzing` or another task id owns it. This prevents the duplicate runs described in A.

**Tests to add**

- `tests/test_rfp_service.py::test_stale_analyzing_ticket_marked_failed` (freeze `updated_at` 30 min in the past → `GET` returns `status="failed"`, `can_retry=True`).
- `::test_recent_analyzing_ticket_not_stale`.
- `tests/test_rfp_intake_task.py::test_soft_time_limit_marks_failed_without_retry` (raise `SoftTimeLimitExceeded` from a mocked `run_rfp_intake`).
- `tests/pipelines/test_rfp_graph_timeout.py`: a worker that sleeps past a tiny timeout → transient error raised.

**Effort:** M (≈1 day).

---

### F. Live status via SSE (PR #52)

**Finding:** PR #52 (`feature/sse-notifications`) was merged on 2026-10-30 20:14 (Europe/Berlin) as `254e8fb`, but into `feature/rfp-approval-completion`, **not into `main`**. `git merge-base --is-ancestor 254e8fb origin/main` is false, and `services/app/domain/rfp_sse.py` does not exist on `main`. In addition, the SSE stream only carries `rfp_ticket_created` (`RFP_TICKET_CREATED_EVENT`, published from the graph after classification). It never publishes status transitions (`failed`, `discarded`, `intake_complete`, drafting, approvals), so even after landing it would not solve D on its own.

**Proposed change** (after D, which is needed anyway as a fallback)

1. Land PR #52's commits on `main` via a dedicated PR from `feature/rfp-approval-completion` (or a cherry-pick PR). It adds one dependency (`redis` Python client), which is already reviewed in that PR.
2. Add `RFP_TICKET_STATUS_CHANGED_EVENT = "rfp_ticket_status_changed"` with a PHI-safe payload `{ticket_id, status, pipeline_stage, can_retry, updated_at}`. Publish it from one place: a helper called by `update_ticket_fields`, `mark_ticket_failed`, `prepare_ticket_retry`, and the drafting/approval status setters.
3. Frontend: on `rfp_ticket_status_changed`, upsert the list row and, if it is the selected ticket, call `loadDetail`. Keep the polling from D as the fallback whenever the EventSource is disconnected.

**Tests to add:** extend `tests/pipelines/test_rfp_sse.py` (from PR #52) with payload key allow-list tests for the new event, plus a service test asserting that one event is published per status transition (Redis publisher mocked).

**Effort:** M (≈1 day after PR #52 is on `main`).

---

## 4. Suggested delivery order

1. **B + A** (one PR, `fix(rfp): terminal failed status for unreadable PDFs`). This gives the biggest user-visible win.
2. **D** (`fix(backoffice): restart RFP polling after actions`). Frontend only.
3. **E** (`fix(rfp): stale intake guard and timeouts`).
4. **C** (`feat(rfp): domain relevance gate in classifier`). Review it with real RFP fixtures.
5. **F** (land PR #52 on `main`, then the status events).

Total ≈ 4–5 developer-days. None of the items needs a database migration unless a dedicated `failure_reason` column is preferred over reusing `discard_reason`.

## 5. Out of scope / noted

- `scripts/seed_inventory_volume.py` creates random consumptions without a stock check. This is unrelated to RFP, but it is the likely source of the negative stock found earlier (see the `fix(inventory)` work in PR #53).
- RFP UI language issues (one Spanish string in this panel) are listed in [`language-check-2026-10-31.md`](./language-check-2026-10-31.md).
