import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

const MedicalSuppliesList = createLazyViewportPanel(
  () =>
    import("@/components/inventory/MedicalSuppliesList").then((mod) => ({
      default: mod.MedicalSuppliesList,
    })),
  {
    minHeight: "50vh",
    label: "Cargando suministros médicos…",
  },
);

export default function InventoryProductsPage() {
  return <MedicalSuppliesList />;
}
