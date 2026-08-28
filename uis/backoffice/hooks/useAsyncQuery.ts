"use client";

import { useCallback, useEffect, useState } from "react";
import type { AsyncStatus } from "@/types/async";

interface UseAsyncQueryOptions<T> {
  queryFn: () => Promise<T>;
  resolveError: (error: unknown) => string;
  initialData?: T;
  enabled?: boolean;
}

export function useAsyncQuery<T>({
  queryFn,
  resolveError,
  initialData,
  enabled = true,
}: UseAsyncQueryOptions<T>) {
  const [data, setData] = useState<T | undefined>(initialData);
  const [status, setStatus] = useState<AsyncStatus>(enabled ? "loading" : "success");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const result = await queryFn();
      setData(result);
      setStatus("success");
    } catch (err) {
      setError(resolveError(err));
      setStatus("error");
    }
  }, [queryFn, resolveError]);

  useEffect(() => {
    if (!enabled) return;
    void reload();
  }, [enabled, reload]);

  return {
    data,
    setData,
    status,
    error,
    isLoading: status === "loading",
    isError: status === "error",
    isSuccess: status === "success",
    reload,
  };
}
