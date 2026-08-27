import Link from "next/link";
import { InventoryOrdersList } from "@/components/inventory/InventoryOrdersList";

export default function InventoryOrdersPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Inventario
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Órdenes de inventario
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Historial de entregas (entrada) y consumos (salida). Sin edición ni
          borrado.
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm font-medium text-blue-700 dark:text-blue-300">
          <Link href="/inventory/products" className="hover:underline">
            ← Suministros
          </Link>
          <Link href="/inventory/orders/inbound" className="hover:underline">
            Registrar entrega
          </Link>
          <Link href="/inventory/orders/outbound" className="hover:underline">
            Registrar consumo
          </Link>
        </div>
      </header>

      <InventoryOrdersList />
    </div>
  );
}
