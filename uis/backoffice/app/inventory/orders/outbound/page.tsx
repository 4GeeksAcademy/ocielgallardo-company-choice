import Link from "next/link";
import { OutboundOrderFormPanel } from "@/components/lazy/lazyViewportPanels";

export default function OutboundOrderPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          Inventory
        </p>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Log usage
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Log clinical use or expiry waste at a HealthCore clinic
          (outbound order / SupplyConsumption). Available stock is shown
          before you submit.
        </p>
        <Link
          href="/inventory/products"
          className="inline-block text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back to supplies
        </Link>
      </header>

      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 shadow-sm sm:p-6">
        <OutboundOrderFormPanel />
      </div>
    </div>
  );
}
