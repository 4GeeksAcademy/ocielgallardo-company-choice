"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const IncidentCreateForm = dynamic(
  () =>
    import("@/components/incidents/IncidentCreateForm").then((mod) => ({
      default: mod.IncidentCreateForm,
    })),
  {
    loading: () => (
      <PanelPlaceholder minHeight={420} label="Cargando formulario de incidente…" />
    ),
  },
);

export default function NewIncidentPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Incident Manager
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Register incident
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Capture operational, compliance, and patient-experience incidents without
          storing identifying patient data.
        </p>
        <Link
          href="/incidents"
          className="inline-block text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back to incident list
        </Link>
      </header>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 shadow-sm sm:p-6">
        <LazyWhenVisible
          fallback={
            <PanelPlaceholder minHeight={420} label="Cargando formulario de incidente…" />
          }
          minHeight={420}
        >
          <IncidentCreateForm />
        </LazyWhenVisible>
      </div>
    </div>
  );
}
