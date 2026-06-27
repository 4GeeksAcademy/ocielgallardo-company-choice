import { Suspense } from "react";
import { CandidateDetailWorkspace } from "@/components/candidates/CandidateDetailWorkspace";

function LoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <p className="text-sm text-slate-600">Cargando candidatura...</p>
    </div>
  );
}

interface CandidatePageProps {
  params: Promise<{ id: string }>;
}

export default async function CandidatePage({ params }: CandidatePageProps) {
  const { id } = await params;

  return (
    <Suspense fallback={<LoadingFallback />}>
      <CandidateDetailWorkspace key={id} candidateId={id} />
    </Suspense>
  );
}
