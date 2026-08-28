"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  fetchInventoryOrders,
  friendlyInventoryError,
} from "@/lib/services/inventoryApi";
import type { InventoryOrder, OrderType } from "@/types/inventory";
import { ORDER_TYPE_LABELS } from "@/types/inventory";
import type { AsyncStatus } from "@/types/async";

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
  const [orders, setOrders] = useState<InventoryOrder[]>([]);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await fetchInventoryOrders();
      setOrders(data);
      setStatus("success");
    } catch (err) {
      setError(
        friendlyInventoryError(
          err,
          "No se pudieron cargar las órdenes. Comprueba que la API esté en marcha."
        )
      );
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
          onClick={() => void load()}
          disabled={status === "loading"}
        >
          {status === "loading" ? "Cargando…" : "Actualizar"}
        </Button>
      </header>

      {status === "loading" && (
        <p className="text-sm text-slate-600 dark:text-slate-300">Cargando órdenes…</p>
      )}

      {status === "error" && error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-800"
        >
          <p>{error}</p>
          <Button
            type="button"
            variant="secondary"
            className="mt-3 text-xs"
            onClick={() => void load()}
          >
            Reintentar
          </Button>
        </div>
      )}

      {status === "success" && orders.length === 0 && (
        <EmptyState
          title="No hay órdenes"
          description="La API no devolvió entregas ni consumos. Registra un movimiento o ejecuta el seed de inventario."
          actionLabel="Reintentar"
          onAction={() => void load()}
        />
      )}

      {status === "success" && orders.length > 0 && (
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
              {orders.map((order) => (
                <tr
                  key={`${order.order_type}-${order.id}`}
                  className="hover:bg-slate-50/80"
                >
                  <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-50">
                    {order.supply_name}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-slate-700 dark:text-slate-200">
                    {order.quantity}
                  </td>
                  <td className="px-4 py-3">
                    <Badge className={ORDER_TYPE_BADGE_CLASSES[order.order_type]}>
                      {ORDER_TYPE_LABELS[order.order_type]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                    {formatCreatedAt(order.created_at)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-200">
                    {order.user_uuid}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
