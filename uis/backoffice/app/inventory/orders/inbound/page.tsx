import { Suspense } from "react";
import Link from "next/link";
import { InboundOrderForm } from "@/components/inventory/InboundOrderForm";

function FormFallback() {
  return <p className="text-sm text-slate-600 dark:text-slate-300">Cargando formulario…</p>;
}

export default function InboundOrderPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Inventario
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Registrar entrega
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Registra una entrega de proveedor recibida en una clínica HealthCore
          (orden de entrada / SupplyDelivery).
        </p>
        <Link
          href="/inventory/products"
          className="inline-block text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Volver a suministros
        </Link>
      </header>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 shadow-sm sm:p-6">
        <Suspense fallback={<FormFallback />}>
          <InboundOrderForm />
        </Suspense>
      </div>
    </div>
  );
}
