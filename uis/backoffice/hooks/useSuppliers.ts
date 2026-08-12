"use client";

import { useCallback, useEffect, useState } from "react";
import type { Supplier } from "@/types/suppliers";
import { fetchSuppliers } from "@/lib/services/suppliersApi";
import type { AsyncStatus } from "@/types/async";
import { friendlyApiErrorEs } from "@/lib/utils/friendlyApiError";

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
      setError(
        friendlyApiErrorEs(err, "No se pudieron cargar los proveedores.")
      );
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
