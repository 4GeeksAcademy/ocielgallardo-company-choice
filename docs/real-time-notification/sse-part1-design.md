# HealthCore — SSE Part 1: Design notes (PR)

BRIEFING: [`heathcore-BRIFING.es.md`](./heathcore-BRIFING.es.md)

## Recovery strategy (chosen)

**Refetch-then-SSE**

1. Mount `/rfp`: `GET /rfp/tickets` loads the canonical list.
2. While SSE is connected: `rfp_ticket_created` **upserts** by `ticket_id` from the event payload (no full list refetch per event).
3. On disconnect: client uses exponential backoff (`rfpSse.ts`).
4. When the stream becomes `connected` again after a reconnect (`onRecovered`): refetch `GET /rfp/tickets` so tickets created while offline are not lost.
5. **Dedup:** list merge and banners key on `ticket_id` (`upsertTicketFromSseEvent`, `dedupeTicketsById`, notice Set).

We did **not** implement Last-Event-ID / server replay: Redis pub/sub is fire-and-forget; the Postgres ticket list is already the source of truth.

## Design Q&A (for PR)

### 1. Independent SSE connections vs shared layer (2 or 50 users)?

Each browser opens its **own** authenticated SSE connection (`GET /rfp/events/stream` + Bearer JWT). Connections are independent so auth, teardown, and reconnect stay per session.

A **shared intermediate layer** is Redis pub/sub (`healthcore:rfp:events`): Celery intake publishes once; each API stream subscriber fans out to its client. Two commercial users → two HTTP streams, one Redis channel. Fifty users → fifty long-lived connections (memory / FD cost on the API). Acceptable for Revenue Cycle scale; if hundreds/thousands, scale API replicas and keep Redis as the fan-out bus — do not multiplex many UIs onto one browser connection.

### 2. Recovery + duplicate avoidance?

Strategy: **refetch-then-SSE** (above). Duplicates avoided by `ticket_id` upsert/dedupe on list and banner. After reconnect, refetch replaces/merges with the server list (also unique by `ticket_id` in DB).

### 3. Why SSE instead of WebSockets? When would it stop fitting?

Part 1 is **server → client push** of a named domain event (`rfp_ticket_created`). SSE matches that (named `event:` / `data:`, HTTP + JWT via `fetch`). WebSockets would work but add bidirectional complexity we do not need here.

SSE stops being enough when the same channel must carry **client → server** reactions (claim ticket, chat ack) — that is Part 2 WebSocket chat in `real-time-communication/`. Ticket actions today stay on REST (`/rfp/...`).

## Manual verification (reconnect + recovery)

Documented checklist (Compose / local):

1. Open backoffice `/rfp` as two authenticated users (or two windows). Confirm “Live updates connected”.
2. Upload a valid institutional RFP PDF (or wait for intake to reach orchestrate). Both UIs show a distinct banner and the ticket in the list **without** manual reload.
3. DevTools → Network: throttle Offline (or stop the backend briefly). UI shows “Live updates reconnecting…”.
4. While offline, create another RFP ticket from a second client/session if possible; restore network.
5. Confirm backoff reconnects, status returns to connected, list **refetches**, new ticket appears, and the same `ticket_id` is **not** duplicated in the list or banner spam.
6. Confirm unauthenticated `GET /rfp/events/stream` returns 401.

Automated coverage: `tests/pipelines/test_rfp_sse.py`, `tests/test_rfp_sse_stream.py` (headers `text/event-stream`, named `event:`, BRIEFING-shaped JSON in `data:`).
