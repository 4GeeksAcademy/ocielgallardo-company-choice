"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import Link from "next/link";

import { IncidentCsvUpload } from "@/components/incidents/IncidentCsvUpload";
import { Button } from "@/components/ui/Button";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";
import {
  analyzeIncidents,
  exportIncidentsResults,
  HealthcoreApiError,
} from "@/lib/services/healthcoreApi";
import { track } from "@/lib/services/telemetry";
import type { IncidentAnalysisSummary } from "@/types/incidents";

const IncidentAnalysisSummaryView = dynamic(
  () =>
    import("@/components/incidents/IncidentAnalysisSummary").then((mod) => ({
      default: mod.IncidentAnalysisSummaryView,
    })),
  {
    loading: () => (
      <PanelPlaceholder minHeight={320} label="Loading analysis summary…" />
    ),
  },
);

export default function IncidentsAnalyzePage() {
  const [summary, setSummary] = useState<IncidentAnalysisSummary | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  async function handleAnalyze() {
    if (!pendingFile) {
      setError("Select a CSV file before analyzing.");
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const result = await analyzeIncidents(pendingFile);
      setSummary(result);
      track("incident_csv_analyzed", { row_count: result?.total ?? 0 });
    } catch (err) {
      setSummary(null);
      if (err instanceof HealthcoreApiError) {
        setError(err.message);
      } else {
        setError("Could not analyze the file. Is the HealthCore API running?");
      }
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleExport() {
    setIsExporting(true);
    setError(null);

    try {
      await exportIncidentsResults();
    } catch (err) {
      if (err instanceof HealthcoreApiError) {
        setError(err.message);
      } else {
        setError("Could not download results CSV.");
      }
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Incident Manager
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Patient Incident Analysis
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Upload a HealthCore incidents CSV, run the same validation and metrics
          pipeline as the CLI, and review totals, category/status breakdowns,
          satisfaction index, and invalid-record rules from CONTEXT.
        </p>
        <Link
          href="/incidents"
          className="inline-block text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back to incident list
        </Link>
      </header>

      <section className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 shadow-sm sm:p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Upload CSV
        </h2>
        <div className="mt-3">
          <IncidentCsvUpload
            disabled={isAnalyzing}
            onFileSelected={(file) => {
              setPendingFile(file);
              setError(null);
            }}
          />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={handleAnalyze}
            disabled={isAnalyzing || !pendingFile}
          >
            {isAnalyzing ? "Analyzing…" : "Analyze CSV"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={handleExport}
            disabled={isExporting || !summary}
          >
            {isExporting ? "Downloading…" : "Download results CSV"}
          </Button>
        </div>
        {error ? (
          <p className="mt-3 text-sm text-red-600 dark:text-red-400" role="alert">
            {error}
          </p>
        ) : null}
      </section>

      {summary ? (
        <LazyWhenVisible
          fallback={
            <PanelPlaceholder minHeight={320} label="Loading analysis summary…" />
          }
          minHeight={320}
        >
          <IncidentAnalysisSummaryView summary={summary} />
        </LazyWhenVisible>
      ) : null}
    </div>
  );
}
