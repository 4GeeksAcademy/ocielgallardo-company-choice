"use client";

import { useCallback, useEffect, useState } from "react";
import type { Application } from "@/types/application";
import type { AsyncStatus } from "@/types/async";
import { ApiError } from "@/lib/services/client";
import { fetchRecords } from "@/lib/services/records";

function resolveErrorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function useRecords() {
  const [records, setRecords] = useState<Application[]>([]);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await fetchRecords(100);
      setRecords(data);
      setStatus("success");
    } catch (err) {
      setError(
        resolveErrorMessage(err, "No se pudieron cargar las candidaturas.")
      );
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    let isActive = true;

    async function bootstrap() {
      try {
        const data = await fetchRecords(100);
        if (!isActive) return;
        setRecords(data);
        setStatus("success");
      } catch (err) {
        if (!isActive) return;
        setError(
          resolveErrorMessage(err, "No se pudieron cargar las candidaturas.")
        );
        setStatus("error");
      }
    }

    void bootstrap();
    return () => {
      isActive = false;
    };
  }, []);

  return {
    records,
    setRecords,
    status,
    isLoading: status === "loading",
    isSuccess: status === "success",
    isError: status === "error",
    error,
    reload: load,
  };
}
