import { Suspense } from "react";
import Link from "next/link";
import { OutboundOrderForm } from "@/components/inventory/OutboundOrderForm";

function FormFallback() {
  return <p className="text-sm text-slate-600">Cargando formulario…</p>;
}

export default function OutboundOrderPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          Inventario
        </p>
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">
          Registrar consumo
        </h1>
        <p className="text-sm text-slate-600">
          Registra un consumo clínico o desecho por caducidad en una clínica
          HealthCore (orden de salida / SupplyConsumption). El stock
          disponible se muestra antes de enviar.
        </p>
        <Link
          href="/inventory/products"
          className="inline-block text-sm font-medium text-blue-700 hover:underline"
        >
          ← Volver a suministros
        </Link>
      </header>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
        <Suspense fallback={<FormFallback />}>
          <OutboundOrderForm />
        </Suspense>
      </div>
    </div>
  );
}
