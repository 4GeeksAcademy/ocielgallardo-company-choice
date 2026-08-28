import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

interface CandidatePageProps {
  params: Promise<{ id: string }>;
}

const CandidateDetailWorkspace = createLazyViewportPanel(
  () =>
    import("@/components/candidates/CandidateDetailWorkspace").then((mod) => ({
      default: mod.CandidateDetailWorkspace as typeof mod.CandidateDetailWorkspace &
        import("react").ComponentType<Record<string, unknown>>,
    })),
  {
    minHeight: "60vh",
    label: "Cargando candidatura…",
  },
);

export default async function CandidatePage({ params }: CandidatePageProps) {
  const { id } = await params;

  return <CandidateDetailWorkspace key={id} candidateId={id} />;
}
