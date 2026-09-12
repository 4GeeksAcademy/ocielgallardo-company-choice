"use client";

import dynamic from "next/dynamic";
import { LazyWhenVisible } from "@/components/ui/LazyWhenVisible";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const MonthlyClinicSupplyPanel = dynamic(
  () =>
    import("@/components/reporting/MonthlyClinicSupplyPanel").then((mod) => ({
      default: mod.MonthlyClinicSupplyPanel,
    })),
  {
    loading: () => (
      <PanelPlaceholder
        minHeight={400}
        label="Loading clinic supply report…"
      />
    ),
  }
);

export default function ReportingPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Leadership
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Monthly Clinic Supply Performance
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Board-ready view of supply cost, consumption activity, critical
          stockout frequency, and expiry risk for each clinic across the US and
          UK network — the numbers Dr. Okonkwo and Claire Whitfield review each
          month, without consolidating spreadsheets.
        </p>
      </header>

      <LazyWhenVisible minHeight={400}>
        <MonthlyClinicSupplyPanel />
      </LazyWhenVisible>
    </div>
  );
}
