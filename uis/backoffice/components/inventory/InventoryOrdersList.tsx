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
  return parsed.toLocaleString("es-ES", {
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
        "No se pudieron cargar las órdenes. Comprueba que la API esté en marcha."
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
            Historial de órdenes
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Entregas y consumos registrados. Esta vista es de solo lectura.
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          className="shrink-0 text-xs"
          onClick={() => void reload()}
          disabled={status === "loading"}
        >
          {status === "loading" ? "Cargando…" : "Actualizar"}
        </Button>
      </header>

      <AsyncRequestPanel
        status={status}
        error={error}
        loadingMessage="Cargando órdenes…"
        onRetry={() => void reload()}
        retryLabel="Reintentar"
      >
        {orders.length === 0 ? (
          <EmptyState
            title="No hay órdenes"
            description="La API no devolvió entregas ni consumos. Registra un movimiento o ejecuta el seed de inventario."
            actionLabel="Reintentar"
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
                  Entregas
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {orderSummary.inboundCount}{" "}
                  <span className="text-sm font-normal text-slate-600 dark:text-slate-300">
                    ({orderSummary.inboundQty} uds)
                  </span>
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Consumos
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                  {orderSummary.outboundCount}{" "}
                  <span className="text-sm font-normal text-slate-600 dark:text-slate-300">
                    ({orderSummary.outboundQty} uds)
                  </span>
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tipo">
              {(
                [
                  { value: "all", label: "Todas" },
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
                title="Sin coincidencias"
                description="No hay órdenes para el filtro seleccionado."
                actionLabel="Ver todas"
                onAction={() => setTypeFilter("all")}
              />
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-sm">
                <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">
                    <tr>
                      <th scope="col" className="px-4 py-3">
                        Producto
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Cantidad
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Tipo
                      </th>
                      <th scope="col" className="px-4 py-3">
                        Fecha
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
