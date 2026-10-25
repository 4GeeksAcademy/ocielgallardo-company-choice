"use client";

import { useCallback, useEffect, useState } from "react";
import { RfpPdfDropzone } from "@/components/rfp/RfpPdfDropzone";
import {
  formatReadability,
  friendlyRfpError,
  getRfpTicket,
  listRfpTickets,
  retryRfpTicket,
  type RfpTicketDetail,
  type RfpTicketSummary,
  uploadRfpPdf,
} from "@/lib/services/rfpApi";

const PIPELINE_STEPS = [
  { id: "converting", label: "Convert PDF" },
  { id: "agents", label: "Classify & workers" },
  { id: "synthesizing", label: "Synthesize" },
  { id: "complete", label: "Done" },
] as const;

function statusLabel(status: string): string {
  switch (status) {
    case "analyzing":
      return "Analyzing";
    case "discarded":
      return "Discarded";
    case "intake_complete":
      return "Intake complete";
    default:
      return status;
  }
}

function statusClass(status: string): string {
  switch (status) {
    case "analyzing":
      return "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200";
    case "discarded":
      return "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200";
    case "intake_complete":
      return "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200";
    default:
      return "bg-slate-100 text-slate-800";
  }
}

function stepIndex(stage: string): number {
  if (stage === "failed") return 0;
  if (stage === "discarded") return -1;
  if (stage === "complete") return 3;
  if (stage === "synthesizing") return 2;
  if (stage === "agents") return 1;
  return 0; // converting / queued
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
  return (
    <ol className="flex flex-wrap gap-2 text-xs">
      {PIPELINE_STEPS.map((step, idx) => {
        const done = !failed && active > idx;
        const current = !failed && active === idx;
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
  );
}

export function RfpIntakePanel() {
  const [tickets, setTickets] = useState<RfpTicketSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RfpTicketDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

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
      return;
    }
    let cancelled = false;
    const tick = async () => {
      try {
        const row = await loadDetail(selectedId);
        if (cancelled) return;
        if (row.status === "analyzing" && !row.last_error) {
          window.setTimeout(() => {
            if (!cancelled) void tick();
          }, 2500);
        } else {
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
            Select a ticket to view intake results for Sales / Revenue Cycle.
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
              </div>
              <p className="font-mono text-xs text-slate-500">{detail.ticket_id}</p>
              <PipelineProgress
                stage={detail.pipeline_stage}
                status={detail.status}
              />
              {detail.status === "analyzing" && !detail.last_error ? (
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Pipeline running… refreshing every few seconds.
                </p>
              ) : null}
              {detail.last_error ? (
                <div className="space-y-2 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
                  <p>
                    Pipeline error (status remains analyzing until retry
                    succeeds): {detail.last_error}
                  </p>
                  {detail.can_retry ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void onRetry()}
                      className="rounded bg-red-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-800 disabled:opacity-60"
                    >
                      Retry pipeline
                    </button>
                  ) : null}
                </div>
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
                  Key aspects by department
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
                  Sales handoff (Part 2 ready)
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
                    ready_for_part2=true — handoff_payload stored on ticket (no
                    re-parse of PDF).
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
