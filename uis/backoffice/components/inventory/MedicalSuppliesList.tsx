"use client";

import { useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { AsyncRequestPanel } from "@/components/ui/AsyncRequestPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { StockLevelBadge } from "@/components/inventory/StockLevelBadge";
import { useAsyncQuery } from "@/hooks/useAsyncQuery";
import {
  fetchMedicalSupplies,
  friendlyInventoryError,
} from "@/lib/services/inventoryApi";
import { track } from "@/lib/services/telemetry";
import type { MedicalSupply } from "@/types/inventory";
import {
  categoryLabel,
  countryLabel,
  unitLabel,
} from "@/types/inventory";

export function MedicalSuppliesList() {
  const resolveError = useCallback(
    (err: unknown) =>
      friendlyInventoryError(
        err,
        "Could not load supplies. Check that the API is running."
      ),
    []
  );

  const queryFn = useCallback(() => fetchMedicalSupplies(), []);

  const { data: supplies, status, error, reload } = useAsyncQuery<MedicalSupply[]>({
    queryFn,
    resolveError,
    initialData: [],
  });

  const items = supplies ?? [];

  /* ── supply_expiry_flagged ────────────────────────────────────────
   * When the product model gains `expiry_date`, this fires for items
   * expiring within 30 days. Until then it checks for the field and
   * only emits when data is available. (Documented plan gap.)
   */
  const expiryChecked = useRef(false);
  useEffect(() => {
    if (status !== "success" || items.length === 0 || expiryChecked.current) return;
    expiryChecked.current = true;
    const now = Date.now();
    const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
    for (const supply of items) {
      const raw = (supply as unknown as Record<string, unknown>)["expiry_date"];
      if (typeof raw === "string") {
        const expiry = new Date(raw).getTime();
        const daysToExpiry = Math.ceil((expiry - now) / (24 * 60 * 60 * 1000));
        if (expiry - now <= THIRTY_DAYS_MS && daysToExpiry >= 0) {
          track("supply_expiry_flagged", {
            clinic_id: 1,
            country: supply.country ?? "US",
            product_id: supply.id,
            product_category: supply.category,
            quantity: supply.current_stock,
            expiry_date: raw,
            days_to_expiry: daysToExpiry,
          });
        }
      }
    }
  }, [items, status]);

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-50">
            Medical supplies
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Current stock per supply. Color levels are display-only
            (critical &lt; 5, low &lt; 15).
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          className="shrink-0 text-xs"
          onClick={() => void reload()}
          disabled={status === "loading"}
        >
          {status === "loading" ? "Loading…" : "Refresh"}
        </Button>
      </header>

      <AsyncRequestPanel
        status={status}
        error={error}
        loadingMessage="Loading supplies…"
        onRetry={() => void reload()}
        retryLabel="Retry"
      >
        {items.length === 0 ? (
          <EmptyState
            title="No supplies"
            description="The API returned no medical supplies. Run the inventory seed or add a new one."
            actionLabel="Retry"
            onAction={() => void reload()}
          />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    Name
                  </th>
                  <th scope="col" className="px-4 py-3">
                    SKU
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Category
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Unit
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Jurisdiction
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Stock actual
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((supply) => (
                  <tr key={supply.id} className="hover:bg-slate-50/80">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-50">
                      {supply.name}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-200">
                      {supply.sku}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                      {categoryLabel(supply.category)}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                      {unitLabel(supply.unit)}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                      {countryLabel(supply.country)}
                    </td>
                    <td className="px-4 py-3">
                      <StockLevelBadge currentStock={supply.current_stock} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:gap-x-3">
                        <Link
                          href={`/inventory/orders/inbound?supply_id=${supply.id}`}
                          className="text-xs font-medium text-blue-700 dark:text-blue-300 hover:underline"
                        >
                          Log delivery
                        </Link>
                        <Link
                          href={`/inventory/orders/outbound?supply_id=${supply.id}`}
                          className="text-xs font-medium text-blue-700 dark:text-blue-300 hover:underline"
                        >
                          Log usage
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncRequestPanel>
    </section>
  );
}
