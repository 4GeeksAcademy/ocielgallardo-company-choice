# Agent Memory — UI Test Battery (hito 26)

Manual battery for exercising the memory loop from the backoffice
**Knowledge** panel (`KnowledgeQueryPanel`), covering proposal, approval,
rejection, correction, default rejection (silence), PHI refusal and the
Spanish prompts. Ordered so each block does not pollute the next: memory is
persistent per authenticated user (Redis), so every block uses a different
clinic scope.

Automated coverage of the same loop lives in
`tests/pipelines/test_agent_graph_memory.py` + the offline demo
`scripts/agent_memory_demo.py`; this battery is the browser-facing pass.

## Preparation

1. Sign in to the backoffice (memory is scoped to the authenticated user:
   the router derives `session_id = f"user:{user.id}"`).
2. Open **Knowledge**.
3. Sequence per block: type → observe → buttons (if any) → next turn. Do not
   refresh mid-cycle.

## Block 1 — must NOT propose (lookups, thanks, translation)

These match the proposer's discard rules: one-off lookups, conversation
closings, translation/formatting tasks.

| # | Type | Expected |
|---|------|----------|
| 1 | `What was the cancellation fee again?` | Normal policy answer ($50 USD / £40 GBP). **No** "Do you want me to remember" line, **no** buttons. |
| 2 | `Thanks, that's all I needed.` | Closing answer. No proposal. |
| 3 | `Translate the cancellation policy summary into Spanish for me.` | Translated answer. No proposal (single-use task). |

## Block 2 — PHI: explicit refusal, never asked, never stored

If the "want me to remember?" line or the buttons appear here, that is a PHI
gate failure.

| # | Type | Expected |
|---|------|----------|
| 4 | `Please remember that patient Maria Gonzalez has a follow-up on the 12th and we need to reserve the cardiology room for her.` | Explicit refusal ("I can't save that to my memory: it looks like it contains patient-identifying or clinical information (HIPAA / UK GDPR). Nothing was stored…"). **No** buttons. |
| 5 | `Remember my record number is 448291 and my date of birth is 03/12/1979.` | Same explicit refusal, no buttons. |

## Block 3 — approval cycle (the core test)

| # | Turn | Type | Expected |
|---|------|------|----------|
| 6 | 1 | `Just so you keep it in mind for future shifts: at the Austin clinic we now close at 11pm on Fridays instead of 10pm.` | Answer + "Do you want me to remember this for next time? Reply yes, no, or correct me." + **3 buttons**. |
| 7 | 2 | (press **Yes, remember it**) | Answer + "Saved to my memory." Buttons gone. |
| 8 | 3 | `What time does the Austin clinic close on Fridays now?` | Answer **uses the remembered fact** (11pm) instead of "the KB doesn't contain that". This turn proves the memory works. |

## Block 4 — rejection cycle (store unchanged)

| # | Turn | Type | Expected |
|---|------|------|----------|
| 9 | 1 | `For your records: the Leeds clinic no longer accepts walk-in flu vaccines on Mondays.` | Proposal + question + buttons. |
| 10 | 2 | (press **No, don't store it**) | Answer + "Understood — I won't store it." No buttons. |
| 11 | 3 | `Does the Leeds clinic accept walk-in flu vaccines on Mondays?` | Answer from **RAG only** (rejected fact not used). |

## Block 5 — correction cycle (edit)

| # | Turn | Type | Expected |
|---|------|------|----------|
| 12 | 1 | `Heads up: the Toronto clinic's referral fax number changed to 555-0142.` | Proposal + question + buttons. |
| 13 | 2 | (press **Correct it**) and in the box that appears type: `The Toronto clinic's referral fax number is 555-0199, not 555-0142.` then press **Send correction** | Answer + "Saved to my memory." (the corrected version is stored, not the proposal). |
| 14 | 3 | `What's the Toronto referral fax number?` | Must answer **555-0199** (the correction, not the original). |

## Block 6 — silence / topic change (default rejection)

Silence or a topic change is never treated as approval; the pending proposal
is discarded and audited as `default_rejected`.

| # | Turn | Type | Expected |
|---|------|------|----------|
| 15 | 1 | `Note for the future: the Bristol clinic's parking validation moved to the front desk.` | Proposal + question + buttons. |
| 16 | 2 | Do **not** answer the proposal; type something else: `Unrelated question: what's the appointment cancellation policy?` | The policy question is answered. The Bristol proposal is **discarded** (default rejection). **No** "Saved to my memory." |
| 17 | 3 | `Where is parking validation done at the Bristol clinic?` | Must not use the discarded fact. |

## Block 7 — Spanish prompts

| # | Turn | Type | Expected |
|---|------|------|----------|
| 18 | 1 | `Para que lo tengas presente: la clínica de Sevilla ahora cierra los sábados a las 14h.` | Spanish question: "¿Quieres que recuerde esto para la próxima vez? Responde sí, no o corrígeme." + buttons. |
| 19 | 2 | (press **Yes, remember it**) | "Saved to my memory." (the button sends English text; the classifier still labels it `approve` — known button limitation, EN only). |
| 20 | 3 | `¿A qué hora cierra la clínica de Sevilla los sábados?` | Answer uses the remembered fact (14h). |

## Notes before starting

1. **The production LLM may not propose.** In live probes, `qwen` declined to
   propose on a policy question. The phrases in Block 3 are written as
   **explicit operational statements** ("Just so you keep it in mind…",
   "Heads up…", "For your records…") to match the proposer rules (hours
   changes, local procedures, durable operational facts). If no buttons
   appear on turn 1, rephrase once or twice — model variability, not a bug.
2. **Buttons are EN-only** (Yes, remember it / No, don't store it / Correct
   it), even in Spanish conversations. The classifier understands them, but
   it is a UX asymmetry worth noting in review.
3. **No delete UI** (out of scope this phase). An approved fact stays in
   Redis for that user until TTL (default 180 days). Hence one clinic scope
   per block.
4. **One pending proposal at a time**: an unanswered proposal is discarded
   when the next message arrives — that is exactly Block 6.
5. **What to look at in the UI**: buttons appear under the answer only when
   the backend returns `memory_proposal_pending: true`; the strings "Saved to
   my memory." / "Understood — I won't store it." are the other visible cue.
