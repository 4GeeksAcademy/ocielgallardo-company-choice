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

  /** Manual refresh (button / retry) — setState from an event handler is fine. */
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

  /**
   * Initial / dependency-driven fetch.
   * Avoid calling reload() here: reload() sets state synchronously before await,
   * which triggers the React Compiler "setState in effect" lint. Status already
   * starts as "loading" when enabled; only update state after the await.
   */
  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    void (async () => {
      try {
        const result = await queryFn();
        if (cancelled) return;
        setData(result);
        setStatus("success");
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(resolveError(err));
        setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [enabled, queryFn, resolveError]);

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
