"use client";

import { RfpIntakePanel } from "@/components/rfp/RfpIntakePanel";

export default function RfpIntakePage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Revenue Cycle
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          RFP intake
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Upload institutional RFPs (PDF). The agentic flow classifies the
          document, extracts metadata, and routes key aspects to Revenue,
          Clinical, and Compliance — without reading the original PDF in the
          ticket view.
        </p>
      </header>
      <RfpIntakePanel />
    </div>
  );
}
