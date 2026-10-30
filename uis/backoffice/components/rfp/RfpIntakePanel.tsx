"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RfpPdfDropzone } from "@/components/rfp/RfpPdfDropzone";
import {
  decideRfpApproval,
  formatReadability,
  friendlyRfpError,
  friendlyRfpLastError,
  getRfpTicket,
  listRfpTickets,
  retryRfpDraft,
  retryRfpTicket,
  startRfpApproval,
  startRfpDraft,
  type DepartmentSection,
  type RfpApprovalDecision,
  type RfpTicketDetail,
  type RfpTicketSummary,
  uploadRfpPdf,
} from "@/lib/services/rfpApi";
import {
  dedupeTicketsById,
  subscribeRfpEvents,
  upsertTicketFromSseEvent,
  type RfpSseConnectionStatus,
  type RfpTicketCreatedEvent,
} from "@/lib/services/rfpSse";

const PIPELINE_STEPS = [
  { id: "converting", label: "Convert PDF" },
  { id: "agents", label: "Classify & workers" },
  { id: "synthesizing", label: "Synthesize" },
  { id: "complete", label: "Intake done" },
] as const;

const DRAFT_STEPS = [
  { id: "drafting", label: "Generate drafts" },
  { id: "under_evaluation", label: "Evaluate" },
  { id: "draft_ready", label: "Ready for approval" },
] as const;

const APPROVAL_STEPS = [
  { id: "waiting_for_approval", label: "Department approvals" },
  { id: "done", label: "Final document" },
] as const;

function statusLabel(status: string): string {
  switch (status) {
    case "analyzing":
      return "Analyzing";
    case "discarded":
      return "Discarded";
    case "intake_complete":
      return "Intake complete";
    case "drafting":
      return "Drafting";
    case "under_evaluation":
      return "Under evaluation";
    case "needs_human_review":
      return "Needs human review";
    case "waiting_for_approval":
      return "Waiting for approval";
    case "done":
      return "Done";
    default:
      return status;
  }
}

function statusClass(status: string): string {
  switch (status) {
    case "analyzing":
    case "drafting":
    case "under_evaluation":
    case "waiting_for_approval":
      return "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200";
    case "discarded":
      return "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200";
    case "intake_complete":
    case "draft_ready":
    case "done":
      return "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200";
    case "needs_human_review":
      return "bg-orange-100 text-orange-900 dark:bg-orange-950 dark:text-orange-200";
    default:
      return "bg-slate-100 text-slate-800";
  }
}

function isPart2Running(status: string, lastError?: string | null): boolean {
  return (
    (status === "drafting" || status === "under_evaluation") && !lastError
  );
}

function stepIndex(stage: string): number {
  if (stage === "failed") return 0;
  if (stage === "discarded") return -1;
  if (stage === "complete" || stage === "drafting" || stage === "under_evaluation" || stage === "draft_ready" || stage === "needs_human_review")
    return 3;
  if (stage === "synthesizing") return 2;
  if (stage === "agents") return 1;
  return 0;
}

function draftStepIndex(stage: string, status: string): number {
  if (status === "waiting_for_approval" || status === "done") return 2;
  if (status === "needs_human_review") return 2;
  if (stage === "draft_ready") return 2;
  if (stage === "under_evaluation" || status === "under_evaluation") return 1;
  if (stage === "drafting" || status === "drafting") return 0;
  return -1;
}

function approvalStepIndex(status: string): number {
  if (status === "done") return 1;
  if (status === "waiting_for_approval") return 0;
  return -1;
}

function approvalBadgeClass(status: string | null | undefined): string {
  switch (status) {
    case "approved":
      return "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200";
    case "rejected":
      return "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200";
    case "request_changes":
      return "bg-orange-100 text-orange-900 dark:bg-orange-950 dark:text-orange-200";
    case "pending":
      return "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200";
    default:
      return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
  }
}

function PipelineProgress({
  stage,
  status,
}: {
  stage: string;
  status: string;
}) {
  if (status === "discarded") {
    return (
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Pipeline stopped at classifier (document discarded).
      </p>
    );
  }
  const active = stepIndex(stage);
  const failed = stage === "failed";
  const showDraft =
    status === "drafting" ||
    status === "under_evaluation" ||
    status === "needs_human_review" ||
    status === "waiting_for_approval" ||
    status === "done" ||
    stage === "draft_ready";
  const draftActive = draftStepIndex(stage, status);
  const approvalActive = approvalStepIndex(status);
  const showApproval =
    status === "waiting_for_approval" || status === "done";

  return (
    <div className="space-y-2">
      <ol className="flex flex-wrap gap-2 text-xs">
        {PIPELINE_STEPS.map((step, idx) => {
          const done = !failed && active > idx;
          const current = !failed && active === idx && !showDraft;
          const isFail = failed && idx === 0;
          return (
            <li
              key={step.id}
              className={`rounded px-2 py-1 font-medium ${
                isFail
                  ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200"
                  : done
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                    : current
                      ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200"
                      : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
              }`}
            >
              {idx + 1}. {step.label}
              {current && status === "analyzing" && !failed ? "…" : ""}
            </li>
          );
        })}
      </ol>
      {showDraft ? (
        <ol className="flex flex-wrap gap-2 text-xs">
          {DRAFT_STEPS.map((step, idx) => {
            const done = draftActive > idx;
            const current = draftActive === idx && !showApproval;
            const nhr = status === "needs_human_review" && idx === 2;
            return (
              <li
                key={step.id}
                className={`rounded px-2 py-1 font-medium ${
                  nhr
                    ? "bg-orange-100 text-orange-900 dark:bg-orange-950 dark:text-orange-200"
                    : done
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                      : current
                        ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200"
                        : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                }`}
              >
                D{idx + 1}. {nhr ? "Provisional → approvals" : step.label}
                {current && isPart2Running(status) ? "…" : ""}
              </li>
            );
          })}
        </ol>
      ) : null}
      {showApproval ? (
        <ol className="flex flex-wrap gap-2 text-xs">
          {APPROVAL_STEPS.map((step, idx) => {
            const done = approvalActive > idx;
            const current = approvalActive === idx;
            return (
              <li
                key={step.id}
                className={`rounded px-2 py-1 font-medium ${
                  done
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                    : current
                      ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200"
                      : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                }`}
              >
                A{idx + 1}. {step.label}
                {current && status === "waiting_for_approval" ? "…" : ""}
              </li>
            );
          })}
        </ol>
      ) : null}
    </div>
  );
}

function EvalChips({ section }: { section: DepartmentSection }) {
  const evals = (section.evaluation_results || {}) as {
    overall_pass?: boolean;
    readability?: { pass?: boolean; details?: string };
    relevance?: { pass?: boolean; missing_aspects?: string[] };
    compliance?: { pass?: boolean; violations?: string[] };
    feedback_for_generator?: string;
  };
  if (!section.draft_content && !evals.overall_pass && !evals.feedback_for_generator) {
    return null;
  }
  const chip = (label: string, ok: boolean | undefined) => (
    <span
      className={`rounded px-1.5 py-0.5 text-xs font-medium ${
        ok
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
          : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200"
      }`}
    >
      {label}: {ok ? "pass" : "fail"}
    </span>
  );
  return (
    <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 dark:border-slate-800">
      <div className="flex flex-wrap gap-2">
        {chip("Readability", evals.readability?.pass)}
        {chip("Relevance", evals.relevance?.pass)}
        {chip("Compliance", evals.compliance?.pass)}
        {chip("Overall", evals.overall_pass)}
        <span className="text-xs text-slate-500">
          iters: {section.iteration_count ?? 0}
        </span>
      </div>
      {evals.compliance?.violations && evals.compliance.violations.length > 0 ? (
        <p className="text-xs text-red-700 dark:text-red-300">
          Violations: {evals.compliance.violations.join(", ")}
        </p>
      ) : null}
      {evals.feedback_for_generator ? (
        <p className="text-xs text-slate-600 dark:text-slate-300">
          Feedback: {evals.feedback_for_generator}
        </p>
      ) : null}
      {section.draft_content ? (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium text-slate-800 dark:text-slate-200">
            Draft preview
          </summary>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs text-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
            {section.draft_content}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

function sseStatusLabel(status: RfpSseConnectionStatus): string {
  switch (status) {
    case "connected":
      return "Live updates connected";
    case "connecting":
      return "Connecting live updates…";
    case "reconnecting":
      return "Live updates reconnecting…";
    case "disconnected":
      return "Live updates disconnected";
    default:
      return status;
  }
}

export function RfpIntakePanel() {
  const [tickets, setTickets] = useState<RfpTicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RfpTicketDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [pollSlow, setPollSlow] = useState(false);
  const [sseStatus, setSseStatus] =
    useState<RfpSseConnectionStatus>("connecting");
  const [liveNotice, setLiveNotice] = useState<string | null>(null);
  /** Banner dedupe: same ticket_id shown at most once until remount. */
  const noticedTicketIds = useRef(new Set<string>());

  const refreshList = useCallback(async () => {
    const rows = await listRfpTickets();
    setTickets(dedupeTicketsById(rows));
  }, []);

  const loadDetail = useCallback(async (ticketId: string) => {
    const row = await getRfpTicket(ticketId);
    setDetail(row);
    return row;
  }, []);

  useEffect(() => {
    void refreshList().catch((err) => {
      setError(friendlyRfpError(err, "No se pudo cargar la lista de tickets."));
    });
  }, [refreshList]);

  useEffect(() => {
    const unsubscribe = subscribeRfpEvents({
      onStatus: setSseStatus,
      // Recovery: after backoff reconnect, refetch list (refetch-then-SSE).
      onRecovered: () => {
        void refreshList().catch(() => {
          /* best-effort catch-up after disconnect */
        });
      },
      onEvent: (event) => {
        if (event.type !== "rfp_ticket_created") {
          return;
        }
        const data = event.data as RfpTicketCreatedEvent;
        // Live path: upsert from payload — do not refetch the full list per event.
        setTickets((prev) => upsertTicketFromSseEvent(prev, data));
        if (!noticedTicketIds.current.has(data.ticket_id)) {
          noticedTicketIds.current.add(data.ticket_id);
          const label =
            data.client_name?.trim() ||
            data.rfp_id ||
            data.ticket_id.slice(0, 8);
          setLiveNotice(
            `New RFP ticket requires processing: ${label} (${data.ticket_id.slice(0, 8)}…) — status ${data.status}`
          );
        }
      },
    });
    return unsubscribe;
  }, [refreshList]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setPollSlow(false);
      return;
    }
    let cancelled = false;
    const startedAt = Date.now();
    setPollSlow(false);
    const tick = async () => {
      try {
        const row = await loadDetail(selectedId);
        if (cancelled) return;
        const approvalBootstrapping =
          row.status === "waiting_for_approval" &&
          !row.last_error &&
          row.departments.every((d) => !d.approval_status);
        const running =
          (row.status === "analyzing" && !row.last_error) ||
          isPart2Running(row.status, row.last_error) ||
          approvalBootstrapping;
        if (running) {
          if (Date.now() - startedAt > 90_000) {
            setPollSlow(true);
          }
          window.setTimeout(() => {
            if (!cancelled) void tick();
          }, 2500);
        } else {
          setPollSlow(false);
          void refreshList();
        }
      } catch (err) {
        if (!cancelled) {
          setError(friendlyRfpError(err, "No se pudo consultar el ticket."));
        }
      }
    };
    void tick();
    return () => {
      cancelled = true;
    };
  }, [selectedId, loadDetail, refreshList]);

  async function onFileSelected(file: File) {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const created = await uploadRfpPdf(file);
      setInfo(`Ticket ${created.ticket_id} creado (${created.status}).`);
      await refreshList();
      setSelectedId(created.ticket_id);
    } catch (err) {
      setError(friendlyRfpError(err, "La subida del PDF falló."));
    } finally {
      setBusy(false);
    }
  }

  async function onRetry() {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const created = await retryRfpTicket(selectedId);
      setInfo(`Reintento encolado (${created.status}).`);
      await loadDetail(selectedId);
      await refreshList();
    } catch (err) {
      setError(friendlyRfpError(err, "No se pudo reintentar el pipeline."));
    } finally {
      setBusy(false);
    }
  }

  async function onStartDraft() {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const created = await startRfpDraft(selectedId);
      setInfo(`Drafting enqueued (${created.status}).`);
      await loadDetail(selectedId);
      await refreshList();
    } catch (err) {
      setError(friendlyRfpError(err, "No se pudo iniciar el borrador."));
    } finally {
      setBusy(false);
    }
  }

  async function onRetryDraft() {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const created = await retryRfpDraft(selectedId);
      setInfo(`Draft retry enqueued (${created.status}).`);
      await loadDetail(selectedId);
      await refreshList();
    } catch (err) {
      setError(friendlyRfpError(err, "No se pudo reintentar el borrador."));
    } finally {
      setBusy(false);
    }
  }

  async function onStartApproval() {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const created = await startRfpApproval(selectedId);
      setInfo(`Approvals started (${created.status}).`);
      await loadDetail(selectedId);
      await refreshList();
    } catch (err) {
      setError(friendlyRfpError(err, "No se pudo iniciar las aprobaciones."));
    } finally {
      setBusy(false);
    }
  }

  async function onDecide(
    departmentId: string,
    decision: RfpApprovalDecision,
  ) {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const row = await decideRfpApproval(selectedId, departmentId, decision);
      setDetail(row);
      setInfo(`${departmentId}: ${decision}`);
      await refreshList();
    } catch (err) {
      setError(friendlyRfpError(err, "No se pudo registrar la decisión."));
    } finally {
      setBusy(false);
    }
  }

  const salesSummary = detail?.handoff_payload?.sales_summary as
    | {
        headline?: string;
        what_to_ask_whom?: Array<{
          contact: string;
          ask: string;
          needs?: unknown[];
          open_questions?: unknown[];
        }>;
        conflicts?: string[];
      }
    | undefined;

  const globalQuestions = (detail?.handoff_payload?.open_questions as
    | unknown[]
    | undefined) || [];

  const canRetryDraft =
    !!detail &&
    (detail.status === "needs_human_review" ||
      ((detail.status === "drafting" || detail.status === "under_evaluation") &&
        (!!detail.last_error || pollSlow)));

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <section className="space-y-4">
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
            Upload institutional RFP
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            PDF only. Creates a ticket in <code>analyzing</code>; the pipeline
            runs in the background. Revenue Cycle (Tom Callahan) owns the ticket.
          </p>
          <RfpPdfDropzone disabled={busy} onFileSelected={onFileSelected} />
          {busy ? (
            <p className="text-sm text-amber-700 dark:text-amber-300">
              Working…
            </p>
          ) : null}
          {info ? (
            <p className="text-sm text-emerald-700 dark:text-emerald-300">{info}</p>
          ) : null}
          {error ? (
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          ) : null}
          <p
            className={`text-xs ${
              sseStatus === "connected"
                ? "text-emerald-700 dark:text-emerald-300"
                : sseStatus === "reconnecting" || sseStatus === "connecting"
                  ? "text-amber-700 dark:text-amber-300"
                  : "text-slate-500"
            }`}
          >
            {sseStatusLabel(sseStatus)}
          </p>
          {liveNotice ? (
            <p
              className="rounded border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-950 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-100"
              role="status"
            >
              {liveNotice}
            </p>
          ) : null}
        </div>

        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
            <h2 className="font-semibold text-slate-900 dark:text-slate-50">
              Tickets
            </h2>
          </div>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {tickets.length === 0 ? (
              <li className="px-4 py-6 text-sm text-slate-500">No tickets yet.</li>
            ) : (
              tickets.map((t) => (
                <li key={t.ticket_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(t.ticket_id)}
                    className={`flex w-full flex-col gap-1 px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/80 ${
                      selectedId === t.ticket_id
                        ? "bg-blue-50/80 dark:bg-blue-950/40"
                        : ""
                    }`}
                  >
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      {t.client_name || t.original_filename || t.ticket_id}
                    </span>
                    <span className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span
                        className={`rounded px-2 py-0.5 font-medium ${statusClass(t.status)}`}
                      >
                        {statusLabel(t.status)}
                      </span>
                      <span className="font-mono">{t.ticket_id.slice(0, 8)}…</span>
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        {!detail ? (
          <p className="text-sm text-slate-500">
            Select a ticket to view intake / draft results for Sales / Revenue Cycle.
          </p>
        ) : (
          <>
            <header className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                  Ticket detail
                </h2>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${statusClass(detail.status)}`}
                >
                  {statusLabel(detail.status)}
                </span>
                {detail.ready_for_part3 ? (
                  <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">
                    ready_for_part3
                  </span>
                ) : null}
              </div>
              <p className="font-mono text-xs text-slate-500">{detail.ticket_id}</p>
              <PipelineProgress
                stage={detail.pipeline_stage}
                status={detail.status}
              />
              {detail.can_start_draft ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onStartDraft()}
                  className="rounded bg-blue-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-800 disabled:opacity-60"
                >
                  Generate draft
                </button>
              ) : null}
              {canRetryDraft ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onRetryDraft()}
                  className="ml-2 rounded bg-orange-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-800 disabled:opacity-60"
                >
                  Retry drafting
                </button>
              ) : null}
              {detail.can_start_approval ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onStartApproval()}
                  className="ml-2 rounded bg-teal-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  {detail.status === "waiting_for_approval"
                    ? "Retry approvals"
                    : "Start approvals"}
                </button>
              ) : null}
              {(detail.status === "analyzing" ||
                isPart2Running(detail.status, detail.last_error)) &&
              !detail.last_error ? (
                <div className="space-y-1 text-sm text-amber-700 dark:text-amber-300">
                  <p>Pipeline running… refreshing every few seconds.</p>
                  {pollSlow ? (
                    <p>
                      This is taking longer than usual. Check the Celery worker
                      or use <strong>Retry drafting</strong> if the status stays
                      stuck.
                    </p>
                  ) : null}
                </div>
              ) : null}
              {detail.last_error && detail.status === "analyzing" ? (
                <div className="space-y-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
                  <p>
                    Intake error (status remains analyzing until retry
                    succeeds): {detail.last_error}
                  </p>
                  {detail.can_retry ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void onRetry()}
                      className="rounded bg-red-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-800 disabled:opacity-60"
                    >
                      Retry intake
                    </button>
                  ) : null}
                </div>
              ) : null}
              {detail.last_error &&
              (detail.status === "drafting" ||
                detail.status === "under_evaluation") ? (
                <div className="space-y-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
                  <p>Drafting error: {friendlyRfpLastError(detail.last_error)}</p>
                </div>
              ) : null}
              {detail.last_error && detail.status === "waiting_for_approval" ? (
                <div className="space-y-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
                  <p>
                    Approval error: {friendlyRfpLastError(detail.last_error)}
                  </p>
                  {detail.can_start_approval ? (
                    <p className="text-xs opacity-90">
                      Use <strong>Retry approvals</strong> above to restart the
                      review flow, then decide again on each department.
                    </p>
                  ) : null}
                </div>
              ) : null}
              {detail.status === "needs_human_review" ? (
                <p className="rounded border border-orange-200 bg-orange-50 p-2 text-sm text-orange-900 dark:border-orange-900 dark:bg-orange-950/40 dark:text-orange-200">
                  One or more sections are <strong>provisional</strong> (iteration
                  limit exhausted). Last drafts + EvaluationResults are kept for
                  Part 3 — the ticket was not discarded.
                </p>
              ) : null}
              {detail.discard_reason ? (
                <p className="rounded border border-slate-200 bg-slate-50 p-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  Discarded: {detail.discard_reason}
                </p>
              ) : null}
            </header>

            {detail.metadata ? (
              <div className="space-y-1 text-sm">
                <h3 className="font-semibold text-slate-900 dark:text-slate-50">
                  Metadata
                </h3>
                <ul className="grid gap-1 text-slate-700 dark:text-slate-300 sm:grid-cols-2">
                  <li>Client: {detail.metadata.client_name ?? "—"}</li>
                  <li>Country: {detail.metadata.client_country ?? "—"}</li>
                  <li>Program: {detail.metadata.program_type ?? "—"}</li>
                  <li>
                    Population: {detail.metadata.covered_population ?? "—"}
                  </li>
                  <li>Deadline: {detail.metadata.deadline ?? "—"}</li>
                  <li>Budget: {detail.metadata.budget_range ?? "—"}</li>
                  <li>
                    FK grade:{" "}
                    {formatReadability(detail.metadata.flesch_kincaid_grade)}
                  </li>
                  <li>
                    Gunning Fog:{" "}
                    {formatReadability(detail.metadata.gunning_fog)}
                  </li>
                  <li>
                    PHI flagged: {detail.metadata.contains_phi ? "yes" : "no"}
                  </li>
                </ul>
              </div>
            ) : null}

            {detail.departments.length > 0 ? (
              <div className="space-y-3">
                <h3 className="font-semibold text-slate-900 dark:text-slate-50">
                  Departments (aspects + drafts)
                </h3>
                {detail.departments.map((dept) => (
                  <article
                    key={dept.department_id}
                    className="rounded border border-slate-200 p-3 dark:border-slate-700"
                  >
                    <h4 className="font-medium text-slate-900 dark:text-slate-50">
                      {dept.department_id}{" "}
                      <span className="text-sm font-normal text-slate-500">
                        → {dept.owner}
                      </span>
                      {dept.contains_phi ? (
                        <span className="ml-2 rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-800 dark:bg-red-950 dark:text-red-200">
                          PHI flagged
                        </span>
                      ) : null}
                      {dept.needs_human_review ? (
                        <span className="ml-2 rounded bg-orange-100 px-1.5 py-0.5 text-xs font-semibold text-orange-900 dark:bg-orange-950 dark:text-orange-200">
                          Provisional / needs human review
                        </span>
                      ) : null}
                      {dept.approval_status ? (
                        <span
                          className={`ml-2 rounded px-1.5 py-0.5 text-xs font-semibold ${approvalBadgeClass(dept.approval_status)}`}
                        >
                          {dept.approval_status}
                          {dept.approver ? ` · ${dept.approver}` : ""}
                        </span>
                      ) : null}
                    </h4>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
                      {dept.key_aspects.map((aspect, idx) => (
                        <li key={idx}>{String(aspect)}</li>
                      ))}
                    </ul>
                    {dept.open_questions.length > 0 ? (
                      <div className="mt-2 text-sm text-amber-800 dark:text-amber-200">
                        <p className="font-medium">Open questions</p>
                        <ul className="list-disc pl-5">
                          {dept.open_questions.map((q, idx) => (
                            <li key={idx}>{String(q)}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    <EvalChips section={dept} />
                    {detail.status === "waiting_for_approval" &&
                    dept.approval_status !== "approved" ? (
                      <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void onDecide(dept.department_id, "approved")}
                          className="rounded bg-emerald-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-800 disabled:opacity-60"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            void onDecide(dept.department_id, "request_changes")
                          }
                          className="rounded bg-orange-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-orange-700 disabled:opacity-60"
                        >
                          Request changes
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void onDecide(dept.department_id, "rejected")}
                          className="rounded bg-red-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-800 disabled:opacity-60"
                        >
                          Reject
                        </button>
                        {(dept.approval_round ?? 0) > 0 ? (
                          <span className="self-center text-xs text-slate-500">
                            rounds: {dept.approval_round}
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : null}

            {detail.conflicts && detail.conflicts.length > 0 ? (
              <div className="space-y-2 text-sm">
                <h3 className="font-semibold text-slate-900 dark:text-slate-50">
                  Arbitration conflicts
                </h3>
                <ul className="space-y-2">
                  {detail.conflicts.map((c, idx) => {
                    const row = c as {
                      trigger_id?: string;
                      arbiter?: string;
                      detail?: string;
                    };
                    return (
                      <li
                        key={idx}
                        className="rounded border border-orange-200 bg-orange-50 p-2 text-orange-950 dark:border-orange-900 dark:bg-orange-950/40 dark:text-orange-100"
                      >
                        <strong>{row.trigger_id || "conflict"}</strong>
                        {row.arbiter ? ` → ${row.arbiter}` : ""}
                        {row.detail ? (
                          <p className="mt-1 text-xs opacity-90">{row.detail}</p>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}

            {detail.final_document ? (
              <div className="space-y-2 border-t border-slate-200 pt-4 dark:border-slate-700">
                <h3 className="font-semibold text-slate-900 dark:text-slate-50">
                  Final document ({detail.final_document.currency})
                </h3>
                <p className="text-xs text-slate-500">
                  Generated {detail.final_document.generated_at}
                </p>
                <details open={detail.status === "done"}>
                  <summary className="cursor-pointer text-sm font-medium text-slate-800 dark:text-slate-200">
                    View markdown
                  </summary>
                  <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-800 dark:bg-slate-800/60 dark:text-slate-100">
                    {detail.final_document.content_markdown}
                  </pre>
                </details>
                <a
                  className="inline-block text-xs font-medium text-blue-700 underline dark:text-blue-300"
                  href={`data:text/markdown;charset=utf-8,${encodeURIComponent(detail.final_document.content_markdown)}`}
                  download={`rfp-${detail.ticket_id.slice(0, 8)}-final.md`}
                >
                  Download markdown
                </a>
              </div>
            ) : null}

            {detail.trace_events && detail.trace_events.length > 0 ? (
              <details className="border-t border-slate-200 pt-4 dark:border-slate-700">
                <summary className="cursor-pointer text-sm font-semibold text-slate-900 dark:text-slate-50">
                  Trace timeline ({detail.trace_events.length})
                </summary>
                <ol className="mt-2 space-y-2 border-l border-slate-200 pl-3 dark:border-slate-700">
                  {detail.trace_events.map((ev, idx) => (
                    <li key={idx} className="text-xs text-slate-700 dark:text-slate-300">
                      <span className="font-mono text-slate-400">
                        {ev.ts ? String(ev.ts).slice(11, 19) : "—"}
                      </span>{" "}
                      <strong>{ev.agent}</strong> · {ev.action}
                      {ev.department_id ? ` · ${ev.department_id}` : ""}
                      {ev.input != null || ev.output != null ? (
                        <details className="mt-1">
                          <summary className="cursor-pointer text-slate-500">
                            input / output
                          </summary>
                          <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-1 dark:bg-slate-800/60">
                            {JSON.stringify(
                              { input: ev.input, output: ev.output },
                              null,
                              2,
                            )}
                          </pre>
                        </details>
                      ) : null}
                    </li>
                  ))}
                </ol>
              </details>
            ) : null}

            {globalQuestions.length > 0 ? (
              <div className="text-sm">
                <h3 className="font-semibold text-slate-900 dark:text-slate-50">
                  Consolidated open questions
                </h3>
                <ul className="mt-1 list-disc pl-5 text-amber-800 dark:text-amber-200">
                  {globalQuestions.map((q, idx) => (
                    <li key={idx}>{String(q)}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {salesSummary ? (
              <div className="space-y-2 border-t border-slate-200 pt-4 dark:border-slate-700">
                <h3 className="font-semibold text-slate-900 dark:text-slate-50">
                  Sales handoff
                </h3>
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  {salesSummary.headline}
                </p>
                <ul className="space-y-2 text-sm">
                  {(salesSummary.what_to_ask_whom || []).map((item) => (
                    <li
                      key={item.contact + item.ask}
                      className="rounded bg-slate-50 p-2 dark:bg-slate-800/60"
                    >
                      <strong>{item.contact}</strong> ({item.ask})
                    </li>
                  ))}
                </ul>
                {detail.ready_for_part2 ? (
                  <p className="text-xs text-emerald-700 dark:text-emerald-300">
                    ready_for_part2=true — generators use handoff_payload (no
                    PDF re-parse).
                  </p>
                ) : null}
              </div>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}
