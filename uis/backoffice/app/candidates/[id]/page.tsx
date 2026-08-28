import { CandidateDetailWorkspacePanel } from "@/components/lazy/lazyViewportPanels";

interface CandidatePageProps {
  params: Promise<{ id: string }>;
}

export default async function CandidatePage({ params }: CandidatePageProps) {
  const { id } = await params;

  return <CandidateDetailWorkspacePanel key={id} candidateId={id} />;
}
