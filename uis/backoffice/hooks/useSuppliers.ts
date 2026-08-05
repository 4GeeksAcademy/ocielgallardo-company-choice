"use client";

import { useCallback, useEffect, useState } from "react";
import type { Supplier } from "@/types/suppliers";
import { SupplierApiError, fetchSuppliers } from "@/lib/services/suppliersApi";
import type { AsyncStatus } from "@/types/async";

function resolveErrorMessage(err: unknown, fallback: string): string {
  return err instanceof SupplierApiError ? err.message : fallback;
}

export function useSuppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await fetchSuppliers();
      setSuppliers(data);
      setStatus("success");
    } catch (err) {
      setError(resolveErrorMessage(err, "No se pudieron cargar los proveedores."));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    suppliers,
    setSuppliers,
    status,
    isLoading: status === "loading",
    isError: status === "error",
    error,
    reload: load,
  };
}