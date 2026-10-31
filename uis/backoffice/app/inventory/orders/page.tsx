import Link from "next/link";
import { InventoryOrdersListPanel } from "@/components/lazy/lazyViewportPanels";

export default function InventoryOrdersPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Inventory
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Inventory orders
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          History of deliveries (inbound) and usage (outbound). Read-only: no
          editing or deleting.
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm font-medium text-blue-700 dark:text-blue-300">
          <Link href="/inventory/products" className="hover:underline">
            ← Supplies
          </Link>
          <Link href="/inventory/orders/inbound" className="hover:underline">
            Log delivery
          </Link>
          <Link href="/inventory/orders/outbound" className="hover:underline">
            Log usage
          </Link>
        </div>
      </header>

      <InventoryOrdersListPanel />
    </div>
  );
}
