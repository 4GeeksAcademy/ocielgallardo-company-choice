"use client";

import { useCallback, useEffect, useState } from "react";
import { RfpPdfDropzone } from "@/components/rfp/RfpPdfDropzone";
import {
  formatReadability,
  friendlyRfpError,
  getRfpTicket,
  listRfpTickets,
  retryRfpDraft,
  retryRfpTicket,
  startRfpDraft,
  type DepartmentSection,
  type RfpTicketDetail,
  type RfpTicketSummary,
  uploadRfpPdf,
} from "@/lib/services/rfpApi";

const PIPELINE_STEPS = [
  { id: "converting", label: "Convert PDF" },
  { id: "agents", label: "Classify & workers" },
  { id: "synthesizing", label: "Synthesize" },
  { id: "complete", label: "Intake done" },
] as const;

const DRAFT_STEPS = [
  { id: "drafting", label: "Generate drafts" },
  { id: "under_evaluation", label: "Evaluate" },
  { id: "draft_ready", label: "Ready Part 3" },
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
    default:
      return status;
  }
}

function statusClass(status: string): string {
  switch (status) {
    case "analyzing":
    case "drafting":
    case "under_evaluation":
      return "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200";
    case "discarded":
      return "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200";
    case "intake_complete":
    case "draft_ready":
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
  if (status === "needs_human_review") return 2;
  if (stage === "draft_ready") return 2;
  if (stage === "under_evaluation" || status === "under_evaluation") return 1;
  if (stage === "drafting" || status === "drafting") return 0;
  return -1;
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
    stage === "draft_ready";
  const draftActive = draftStepIndex(stage, status);

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
            const current = draftActive === idx;
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
                D{idx + 1}. {nhr ? "Provisional → Part 3" : step.label}
                {current && isPart2Running(status) ? "…" : ""}
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

export function RfpIntakePanel() {
  const [tickets, setTickets] = useState<RfpTicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RfpTicketDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [pollSlow, setPollSlow] = useState(false);

  const refreshList = useCallback(async () => {
    const rows = await listRfpTickets();
    setTickets(rows);
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
        const running =
          (row.status === "analyzing" && !row.last_error) ||
          isPart2Running(row.status, row.last_error);
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
                  <p>Drafting error: {detail.last_error}</p>
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
                  </article>
                ))}
              </div>
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
