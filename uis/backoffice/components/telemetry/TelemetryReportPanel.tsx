"use client";

import { useCallback } from "react";
import { AsyncRequestPanel } from "@/components/ui/AsyncRequestPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAsyncQuery } from "@/hooks/useAsyncQuery";
import {
  fetchTelemetryReport,
  friendlyTelemetryError,
} from "@/lib/services/telemetryApi";
import type { TelemetryReport } from "@/types/telemetry";

function formatRate(rate: number): string {
  return `${(rate * 100).toFixed(2)}%`;
}

function formatPeriodInstant(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

function MetricTable({
  title,
  question,
  headers,
  rows,
  emptyLabel,
}: {
  title: string;
  question: string;
  headers: string[];
  rows: (string | number)[][];
  emptyLabel: string;
}) {
  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 sm:p-5">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
          {title}
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">{question}</p>
      </header>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">{emptyLabel}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                {headers.map((h) => (
                  <th
                    key={h}
                    className="px-2 py-2 font-semibold text-slate-700 dark:text-slate-200"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr
                  key={`${title}-${idx}`}
                  className="border-b border-slate-100 dark:border-slate-800"
                >
                  {row.map((cell, cellIdx) => (
                    <td
                      key={`${title}-${idx}-${cellIdx}`}
                      className="px-2 py-2 text-slate-800 dark:text-slate-100"
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function TelemetryReportPanel() {
  const resolveError = useCallback(
    (err: unknown) =>
      friendlyTelemetryError(
        err,
        "Could not load the telemetry report. Check that the API and Supabase are running."
      ),
    []
  );

  const queryFn = useCallback(() => fetchTelemetryReport(), []);

  const { data, status, error, reload } = useAsyncQuery<TelemetryReport>({
    queryFn,
    resolveError,
  });

  return (
    <AsyncRequestPanel
      status={status}
      error={error}
      loadingMessage="Loading operational telemetry report…"
      onRetry={() => void reload()}
    >
      {!data ? (
        <EmptyState
          title="No report data"
          description="The telemetry report endpoint returned nothing."
          actionLabel="Retry"
          onAction={() => void reload()}
        />
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-100">
            <p className="font-semibold">Period (UTC)</p>
            <p className="mt-1">
              from <span className="font-mono">{formatPeriodInstant(data.period.from)}</span>
              {" → "}
              to <span className="font-mono">{formatPeriodInstant(data.period.to)}</span>
            </p>
            <p className="mt-1 text-xs opacity-80">
              Default window is the last 7 days when no query dates are provided.
            </p>
          </div>

          <MetricTable
            title="events_per_day"
            question="How many telemetry events does the system emit each day?"
            headers={["date", "count"]}
            emptyLabel="No events in this period."
            rows={data.metrics.events_per_day.map((r) => [r.date, r.count])}
          />

          <MetricTable
            title="error_rate_by_type"
            question="Which error event types dominate, relative to daily volume?"
            headers={["date", "event_type", "error_count", "total_count", "rate"]}
            emptyLabel="No error events in this period."
            rows={data.metrics.error_rate_by_type.map((r) => [
              r.date,
              r.event_type,
              r.error_count,
              r.total_count,
              formatRate(r.rate),
            ])}
          />

          <MetricTable
            title="avg_latency_by_path"
            question="Which API paths are slowest (mean duration_ms)?"
            headers={["date", "path", "avg_duration_ms", "sample_count"]}
            emptyLabel="No api_latency_recorded events in this period."
            rows={data.metrics.avg_latency_by_path.map((r) => [
              r.date,
              r.path,
              r.avg_duration_ms,
              r.sample_count,
            ])}
          />

          <MetricTable
            title="auth_failure_rate"
            question="What share of login attempts fail each day?"
            headers={["date", "failed", "succeeded", "total_attempts", "rate"]}
            emptyLabel="No login events in this period."
            rows={data.metrics.auth_failure_rate.map((r) => [
              r.date,
              r.failed,
              r.succeeded,
              r.total_attempts,
              formatRate(r.rate),
            ])}
          />
        </div>
      )}
    </AsyncRequestPanel>
  );
}
