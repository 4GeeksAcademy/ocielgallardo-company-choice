import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

const ApplicationsWorkspace = createLazyViewportPanel(
  () =>
    import("@/components/ApplicationsWorkspace").then((mod) => ({
      default: mod.ApplicationsWorkspace,
    })),
  {
    minHeight: "60vh",
    label: "Cargando pipeline de candidaturas…",
  },
);

export default function ApplicationsPage() {
  return <ApplicationsWorkspace />;
}
