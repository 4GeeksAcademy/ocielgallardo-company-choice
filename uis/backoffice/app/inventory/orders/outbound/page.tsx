import Link from "next/link";
import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

const OutboundOrderForm = createLazyViewportPanel(
  () =>
    import("@/components/inventory/OutboundOrderForm").then((mod) => ({
      default: mod.OutboundOrderForm,
    })),
  {
    minHeight: 360,
    label: "Cargando formulario de consumo…",
  },
);

export default function OutboundOrderPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Inventario
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Registrar consumo
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Registra un consumo clínico o desecho por caducidad en una clínica
          HealthCore (orden de salida / SupplyConsumption). El stock
          disponible se muestra antes de enviar.
        </p>
        <Link
          href="/inventory/products"
          className="inline-block text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Volver a suministros
        </Link>
      </header>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 shadow-sm sm:p-6">
        <OutboundOrderForm />
      </div>
    </div>
  );
}
