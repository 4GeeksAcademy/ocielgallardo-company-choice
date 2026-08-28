"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const IncidentListPanel = dynamic(
  () =>
    import("@/components/incidents/IncidentListPanel").then((mod) => ({
      default: mod.IncidentListPanel,
    })),
  {
    loading: () => (
      <PanelPlaceholder minHeight={400} label="Cargando listado de incidentes…" />
    ),
  },
);

export default function IncidentsPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Incident Manager
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Browse, filter, and update HealthCore incidents across clinics. Register
          new reports from the form, or open the summary for executive metrics.
        </p>
        <div className="flex flex-wrap gap-2 pt-1 text-sm">
          <Link
            href="/incidents/new"
            className="rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 font-medium text-blue-800 hover:bg-blue-100"
          >
            Register incident
          </Link>
          <Link
            href="/incidents/summary"
            className="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 font-medium text-slate-700 dark:text-slate-200 hover:border-blue-200 dark:hover:border-blue-500 hover:text-blue-700 dark:hover:text-blue-300"
          >
            Summary
          </Link>
          <Link
            href="/incidents/analyze"
            className="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 font-medium text-slate-700 dark:text-slate-200 hover:border-blue-200 dark:hover:border-blue-500 hover:text-blue-700 dark:hover:text-blue-300"
          >
            CSV analyzer
          </Link>
        </div>
      </header>

      <LazyWhenVisible
        fallback={
          <PanelPlaceholder minHeight={400} label="Cargando listado de incidentes…" />
        }
        minHeight={400}
      >
        <IncidentListPanel />
      </LazyWhenVisible>
    </div>
  );
}
