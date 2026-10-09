"use client";

import dynamic from "next/dynamic";
import { PanelPlaceholder } from "@/components/ui/PanelPlaceholder";

const KnowledgeQueryPanel = dynamic(
  () =>
    import("@/components/knowledge/KnowledgeQueryPanel").then((mod) => ({
      default: mod.KnowledgeQueryPanel,
    })),
  {
    loading: () => (
      <PanelPlaceholder minHeight={300} label="Loading knowledge assistant…" />
    ),
  }
);

export default function KnowledgePage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Front desk
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Knowledge assistant
        </h1>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Answers from clinic policies and procedures for patient
          coordinators. Generated from retrieved sources — never invents
          coverage or fees.
        </p>
      </header>

      <KnowledgeQueryPanel />
    </div>
  );
}
