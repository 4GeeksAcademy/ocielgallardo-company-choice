"use client";

import Link from "next/link";
import { IncidentSummaryPanel } from "@/components/incidents/IncidentSummaryPanel";

export default function IncidentSummaryPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          Incident Manager
        </p>
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
          Incident summary
        </h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Aggregated totals by status, category, origin, and branch for HealthCore
          leadership and compliance review.
        </p>
        <Link
          href="/incidents"
          className="inline-block text-sm font-medium text-blue-700 hover:underline"
        >
          ← Back to incident list
        </Link>
      </header>

      <IncidentSummaryPanel />
    </div>
  );
}
