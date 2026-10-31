"use client";

import { useCallback, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { AsyncRequestPanel } from "@/components/ui/AsyncRequestPanel";
import { useAsyncQuery } from "@/hooks/useAsyncQuery";
import {
  fetchInventoryOrders,
  friendlyInventoryError,
} from "@/lib/services/inventoryApi";
import type { InventoryOrder, OrderType } from "@/types/inventory";
import { ORDER_TYPE_LABELS } from "@/types/inventory";

type OrderTypeFilter = "all" | OrderType;

const ORDER_TYPE_BADGE_CLASSES: Record<OrderType, string> = {
  inbound: "bg-emerald-50 text-emerald-700 dark:text-emerald-400 ring-emerald-600/20",
  outbound: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 ring-amber-600/20",
};

function formatCreatedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("en-US", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function InventoryOrdersList() {
  const [typeFilter, setTypeFilter] = useState<OrderTypeFilter>("all");

  const resolveError = useCallback(
    (err: unknown) =>
      friendlyInventoryError(
        err,
        "Could not load orders. Check that the API is running."
      ),
    []
  );

  const queryFn = useCallback(() => fetchInventoryOrders(), []);

  const { data: ordersData, status, error, reload } = useAsyncQuery<InventoryOrder[]>({
    queryFn,
    resolveError,
    initialData: [],
  });

  const orders = ordersData ?? [];

  /** Aggregate counts/quantities over the full payload (thousands of rows after volume seed). */
  const orderSummary = useMemo(() => {
    let inboundCount = 0;
    let outboundCount = 0;
    let inboundQty = 0;
    let outboundQty = 0;
    for (const order of orders) {
      if (order.order_type === "inbound") {
        inboundCount += 1;
        inboundQty += order.quantity;
      } else {
        outboundCount += 1;
        outboundQty += order.quantity;
      }
    }
    return {
      total: orders.length,
      inboundCount,
      outboundCount,
      inboundQty,
      outboundQty,
    };
  }, [orders]);

  /** Client-side type filter — recalculate only when orders or filter change. */
  const filteredOrders = useMemo(() => {
    if (typeFilter === "all") {
      return orders;
    }
    return orders.filter((order) => order.order_type === typeFilter);
  }, [orders, typeFilter]);

  /**
   * Precompute locale date labels for visible rows so `toLocaleString` does not
   * run again on every parent re-render (e.g. filter chip focus / button state).
   */
  const displayRows = useMemo(
    () =>
      filteredOrders.map((order) => ({
        key: `${order.order_type}-${order.id}`,
        supplyName: order.supply_name,
        quantity: order.quantity,
        orderType: order.order_type,
        createdAtLabel: formatCreatedAt(order.created_at),
        userUuid: order.user_uuid,
      })),
    [filteredOrders]
  );

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-50">
            Order history
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Logged deliveries and usage. This view is read-only.
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
        loadingMessage="Loading orders…"
        onRetry={() => void reload()}
        retryLabel="Retry"
      >
        {orders.length === 0 ? (
          <EmptyState
            title="No orders"
            description="The API returned no deliveries or usage. Log a movement or run the inventory seed."
            actionLabel="Retry"
            onAction={() => void reload()}
          />
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Total
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {orderSummary.total}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Deliveries
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {orderSummary.inboundCount}{" "}
                  <span className="text-sm font-normal text-slate-600 dark:text-slate-300">
                    ({orderSummary.inboundQty} units)
                  </span>
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Usage
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {orderSummary.outboundCount}{" "}
                  <span className="text-sm font-normal text-slate-600 dark:text-slate-300">
                    ({orderSummary.outboundQty} units)
                  </span>
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by type">
              {(
                [
                  { value: "all", label: "All" },
                  { value: "inbound", label: ORDER_TYPE_LABELS.inbound },
                  { value: "outbound", label: ORDER_TYPE_LABELS.outbound },
                ] as const
              ).map((option) => (
                <Button
                  key={option.value}
                  type="button"
                  variant={typeFilter === option.value ? "primary" : "secondary"}
                  className="text-xs"
                  onClick={() => setTypeFilter(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>

            {displayRows.length === 0 ? (
              <EmptyState
                title="No matches"
                description="No orders for the selected filter."
                actionLabel="Show all"
                onAction={() => setTypeFilter("all")}
              />
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
                <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                    <tr>
                      <th scope="col" className="px-4 py-3">
                        Product
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Quantity
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Type
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Date
                      </th>
                      <th scope="col" className="px-4 py-3">
                        user_uuid
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {displayRows.map((row) => (
                      <tr key={row.key} className="hover:bg-slate-50/80">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-50">
                          {row.supplyName}
                        </td>
                        <td className="px-4 py-3 tabular-nums text-slate-700 dark:text-slate-200">
                          {row.quantity}
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={ORDER_TYPE_BADGE_CLASSES[row.orderType]}>
                            {ORDER_TYPE_LABELS[row.orderType]}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                          {row.createdAtLabel}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-200">
                          {row.userUuid}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </AsyncRequestPanel>
    </section>
  );
}
