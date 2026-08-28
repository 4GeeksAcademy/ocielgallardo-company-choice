"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const IncidentSummaryPanel = dynamic(
  () =>
    import("@/components/incidents/IncidentSummaryPanel").then((mod) => ({
      default: mod.IncidentSummaryPanel,
    })),
  {
    loading: () => (
      <PanelPlaceholder minHeight={360} label="Cargando resumen de incidentes…" />
    ),
  },
);

export default function IncidentSummaryPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Incident Manager
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Incident summary
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300">
          Aggregated totals by status, category, origin, and branch for HealthCore
          leadership and compliance review.
        </p>
        <Link
          href="/incidents"
          className="inline-block text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back to incident list
        </Link>
      </header>

      <LazyWhenVisible
        fallback={
          <PanelPlaceholder minHeight={360} label="Cargando resumen de incidentes…" />
        }
        minHeight={360}
      >
        <IncidentSummaryPanel />
      </LazyWhenVisible>
    </div>
  );
}
