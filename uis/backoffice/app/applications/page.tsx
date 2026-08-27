import { Suspense } from "react";
import { ApplicationsWorkspace } from "@/components/ApplicationsWorkspace";

function LoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-800">
      <p className="text-sm text-slate-600 dark:text-slate-300">Cargando pipeline de candidaturas...</p>
    </div>
  );
}

export default function ApplicationsPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ApplicationsWorkspace />
    </Suspense>
  );
}
