import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

const SuppliersWorkspace = createLazyViewportPanel(
  () =>
    import("@/components/SuppliersWorkspace").then((mod) => ({
      default: mod.SuppliersWorkspace,
    })),
  {
    minHeight: "60vh",
    label: "Cargando directorio de proveedores…",
  },
);

export default function SuppliersPage() {
  return <SuppliersWorkspace />;
}
