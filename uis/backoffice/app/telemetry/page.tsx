"use client";

import dynamic from "next/dynamic";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const TelemetryReportPanel = dynamic(
  () =>
    import("@/components/telemetry/TelemetryReportPanel").then((mod) => ({
      default: mod.TelemetryReportPanel,
    })),
  {
    loading: () => (
      <PanelPlaceholder
        minHeight={400}
        label="Loading telemetry report…"
      />
    ),
  }
);

export default function TelemetryPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Engineering
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Telemetry report
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Operational health view for the HealthCore backoffice: event volume,
          error rates, API latency, and login failure rate. Not a business
          dashboard.
        </p>
      </header>

      <LazyWhenVisible minHeight={400}>
        <TelemetryReportPanel />
      </LazyWhenVisible>
    </div>
  );
}
