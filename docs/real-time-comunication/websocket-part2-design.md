# HealthCore — WebSocket chat Part 2: design notes (PR)

BRIEFING: [`healthcore-BRIEFING(parte-2).es.md`](./healthcore-BRIEFING(parte-2).es.md)

## Design Q&A

### 1. Why WebSockets (not Part 1 SSE)?

Part 1 SSE is **server → client only** (RFP ticket push). Compliance chat needs the client to send `user_message` and `interrupt_requested` **while** the server is still emitting `token_chunk`. That simultaneous reverse path is what forces a **bidirectional** channel — WebSocket.

### 2. Multiple subscribers, one agent run?

Production is decoupled via in-memory pub/sub on `chat.<session_id>`. One generation task publishes events; every subscribed WebSocket queue receives the same envelopes. A supervisor tab reconnecting with the same `session_id` gets `session_snapshot` plus live fan-out — the agent is **not** invoked once per socket.

### 3. Stream abort vs LangGraph HITL `interrupt()`?

Abort uses a **cancel flag** + `GenerationInterrupted` while streaming LLM tokens (`generate_answer_stream`). We do **not** use LangGraph HITL `interrupt()` for this (that is for RFP approval pauses). On abort: stop further `token_chunk`s, keep the partial assistant message with `status=interrupted`, then start a **new** turn from `new_input` (new message ids — do not overwrite the interrupted bubble).

## Manual verification

1. Open `/knowledge`, confirm “Chat connected” and a `session_id`.
2. Ask a long compliance question — tokens appear live.
3. Mid-stream: Interrupt with redirect text (e.g. UK GDPR). Partial reply stays labeled interrupted; new answer is a separate turn.
4. DevTools offline → online: same `session_id` restores history via `session_snapshot` (not an empty chat).
5. Connect without `?token=` → rejected before chat events.

## Automated tests

`tests/test_agent_chat_ws.py` — auth reject, `token_chunk` + `generation_completed`, interrupt + partial `interrupted`, reconnect snapshot restore.
