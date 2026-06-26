import { Suspense } from "react";
import { CandidateDetailWorkspace } from "@/components/candidates/CandidateDetailWorkspace";

function LoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <p className="text-sm text-slate-600">Cargando candidatura...</p>
    </div>
  );
}

export default function CandidatePage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <CandidateDetailWorkspace />
    </Suspense>
  );
}
