"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StockLevelBadge } from "@/components/inventory/StockLevelBadge";
import {
  fetchMedicalSupplies,
  friendlyInventoryError,
} from "@/lib/services/inventoryApi";
import type { MedicalSupply } from "@/types/inventory";
import {
  categoryLabel,
  countryLabel,
  unitLabel,
} from "@/types/inventory";
import type { AsyncStatus } from "@/types/async";

export function MedicalSuppliesList() {
  const [supplies, setSupplies] = useState<MedicalSupply[]>([]);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await fetchMedicalSupplies();
      setSupplies(data);
      setStatus("success");
    } catch (err) {
      setError(
        friendlyInventoryError(
          err,
          "No se pudieron cargar los suministros. Comprueba que la API esté en marcha."
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
          <h2 className="text-xl font-semibold text-slate-900">
            Suministros médicos
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Stock actual por suministro. Los niveles de color son solo de
            interfaz (crítico &lt; 5, bajo &lt; 15).
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
        <p className="text-sm text-slate-600">Cargando suministros…</p>
      )}

      {status === "error" && error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
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

      {status === "success" && supplies.length === 0 && (
        <EmptyState
          title="No hay suministros"
          description="La API no devolvió suministros médicos. Ejecuta el seed de inventario o registra uno nuevo."
          actionLabel="Reintentar"
          onAction={() => void load()}
        />
      )}

      {status === "success" && supplies.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <tr>
                <th scope="col" className="px-4 py-3">
                  Nombre
                </th>
                <th scope="col" className="px-4 py-3">
                  SKU
                </th>
                <th scope="col" className="px-4 py-3">
                  Categoría
                </th>
                <th scope="col" className="px-4 py-3">
                  Unidad
                </th>
                <th scope="col" className="px-4 py-3">
                  Jurisdicción
                </th>
                <th scope="col" className="px-4 py-3">
                  Stock actual
                </th>
                <th scope="col" className="px-4 py-3">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {supplies.map((supply) => (
                <tr key={supply.id} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {supply.name}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">
                    {supply.sku}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {categoryLabel(supply.category)}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {unitLabel(supply.unit)}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {countryLabel(supply.country)}
                  </td>
                  <td className="px-4 py-3">
                    <StockLevelBadge currentStock={supply.current_stock} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:gap-x-3">
                      <Link
                        href={`/inventory/orders/inbound?supply_id=${supply.id}`}
                        className="text-xs font-medium text-blue-700 hover:underline"
                      >
                        Registrar entrega
                      </Link>
                      <Link
                        href={`/inventory/orders/outbound?supply_id=${supply.id}`}
                        className="text-xs font-medium text-blue-700 hover:underline"
                      >
                        Registrar consumo
                      </Link>
                    </div>
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
