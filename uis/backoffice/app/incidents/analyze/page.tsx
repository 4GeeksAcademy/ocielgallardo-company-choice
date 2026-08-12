"use client";

import { useState } from "react";
import Link from "next/link";

import { IncidentAnalysisSummaryView } from "@/components/incidents/IncidentAnalysisSummary";
import { IncidentCsvUpload } from "@/components/incidents/IncidentCsvUpload";
import { Button } from "@/components/ui/Button";
import {
  analyzeIncidents,
  exportIncidentsResults,
} from "@/lib/services/healthcoreApi";
import type { IncidentAnalysisSummary } from "@/types/incidents";
import { friendlyApiError } from "@/lib/utils/friendlyApiError";

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
    } catch (err) {
      setSummary(null);
      setError(
        friendlyApiError(
          err,
          "Could not analyze the file. Check the HealthCore API and try again."
        )
      );
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
      setError(
        friendlyApiError(err, "Could not download results CSV.")
      );
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          Incident Manager
        </p>
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
          Patient Incident Analysis
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 sm:text-base">
          Upload a HealthCore incidents CSV, run the same validation and metrics
          pipeline as the CLI, and review totals, category/status breakdowns,
          satisfaction index, and invalid-record rules from CONTEXT.
        </p>
        <Link
          href="/incidents"
          className="inline-block text-sm font-medium text-blue-700 hover:underline"
        >
          ← Back to incident list
        </Link>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
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
          <div className="mt-3 space-y-2" role="alert">
            <p className="text-sm text-red-600">{error}</p>
            {pendingFile ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => void handleAnalyze()}
                disabled={isAnalyzing}
              >
                Retry analysis
              </Button>
            ) : null}
          </div>
        ) : null}
      </section>

      {summary ? <IncidentAnalysisSummaryView summary={summary} /> : null}
    </div>
  );
}
