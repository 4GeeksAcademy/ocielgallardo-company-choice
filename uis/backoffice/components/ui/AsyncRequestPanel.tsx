import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import type { AsyncStatus } from "@/types/async";

interface AsyncRequestPanelProps {
  status: AsyncStatus;
  error: string | null;
  loadingMessage?: string;
  onRetry?: () => void;
  retryLabel?: string;
  children: ReactNode;
}

export function AsyncRequestPanel({
  status,
  error,
  loadingMessage = "Loading…",
  onRetry,
  retryLabel = "Retry",
  children,
}: AsyncRequestPanelProps) {
  if (status === "loading") {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
        {loadingMessage}
      </div>
    );
  }

  if (status === "error" && error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-950/40">
        <p className="text-sm text-red-700 dark:text-red-400" role="alert">
          {error}
        </p>
        {onRetry ? (
          <Button className="mt-4" type="button" onClick={onRetry}>
            {retryLabel}
          </Button>
        ) : null}
      </div>
    );
  }

  return <>{children}</>;
}
