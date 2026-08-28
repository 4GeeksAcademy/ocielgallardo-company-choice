"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  fetchIncidentSummary,
  friendlyIncidentError,
} from "@/lib/services/incidentsManagerApi";
import type { IncidentSummary } from "@/types/incidentManager";
import {
  branchLabel,
  categoryLabel,
  originLabel,
  statusLabel,
} from "@/types/incidentManager";
import type { AsyncStatus } from "@/types/async";

function MetricTable({
  title,
  rows,
  labelFor,
}: {
  title: string;
  rows: Record<string, number>;
  labelFor: (key: string) => string;
}) {
  const entries = Object.entries(rows).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return (
    <section className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {title}
      </h2>
      <ul className="mt-3 space-y-1.5 text-sm">
        {entries.map(([key, value]) => (
          <li key={key} className="flex items-center justify-between gap-3">
            <span className="text-slate-700 dark:text-slate-200">{labelFor(key)}</span>
            <span className="font-semibold tabular-nums text-slate-900 dark:text-slate-50">{value}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function IncidentSummaryPanel() {
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await fetchIncidentSummary();
      setSummary(data);
      setStatus("success");
    } catch (err) {
      setSummary(null);
      setError(
        friendlyIncidentError(
          err,
          "Could not load the incident summary. The rest of the app is still available."
        )
      );
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (status === "loading") {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 text-sm text-slate-600 dark:text-slate-300">
        Loading summary metrics…
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 p-6">
        <p className="text-sm text-amber-900" role="alert">
          {error}
        </p>
        <Button className="mt-4" type="button" onClick={() => void load()}>
          Retry summary
        </Button>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Total incidents in the store:{" "}
        <span className="font-semibold text-slate-900 dark:text-slate-50">{summary.total}</span>
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <MetricTable
          title="By status"
          rows={summary.by_status}
          labelFor={statusLabel}
        />
        <MetricTable
          title="By category"
          rows={summary.by_category}
          labelFor={categoryLabel}
        />
        <MetricTable
          title="By origin"
          rows={summary.by_origin}
          labelFor={originLabel}
        />
        <MetricTable
          title="By branch"
          rows={summary.by_branch}
          labelFor={branchLabel}
        />
      </div>
    </div>
  );
}
