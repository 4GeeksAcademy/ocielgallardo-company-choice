import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import type { AsyncStatus } from "@/types/async";

interface CardStateProps {
  status: AsyncStatus;
  error?: string | null;
  onRetry?: () => void;
  /** True when the request succeeded but there is nothing to chart. */
  isEmpty?: boolean;
  emptyMessage?: string;
  minHeight?: number;
  children: ReactNode;
}

/** Loading / error / empty handling shared by every dashboard widget. */
export function CardState({
  status,
  error,
  onRetry,
  isEmpty = false,
  emptyMessage = "No data yet.",
  minHeight = 96,
  children,
}: CardStateProps) {
  if (status === "loading") {
    return (
      <div className="animate-pulse space-y-2" style={{ minHeight }} aria-busy="true">
        <span className="sr-only">Loading…</span>
        <div className="h-3 w-2/3 rounded bg-slate-100 dark:bg-slate-800" />
        <div className="h-3 w-1/2 rounded bg-slate-100 dark:bg-slate-800" />
        <div className="h-3 w-3/4 rounded bg-slate-100 dark:bg-slate-800" />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col items-start gap-2 text-sm" style={{ minHeight }} role="status">
        <p className="text-slate-600 dark:text-slate-300">{error ?? "Could not load data."}</p>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-md text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Retry
          </button>
        ) : null}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <p className="flex items-center text-sm text-slate-500 dark:text-slate-400" style={{ minHeight }}>
        {emptyMessage}
      </p>
    );
  }

  return <>{children}</>;
}

interface DashboardCardProps {
  title: string;
  subtitle?: string;
  href?: string;
  linkLabel?: string;
  children: ReactNode;
  className?: string;
}

/** White surface card with a heading row and optional "view" link. */
export function DashboardCard({ title, subtitle, href, linkLabel = "View", children, className = "" }: DashboardCardProps) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900 ${className}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-50">{title}</h3>
          {subtitle ? <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p> : null}
        </div>
        {href ? (
          <Link
            href={href}
            className="inline-flex shrink-0 items-center gap-1 rounded-md text-xs font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            {linkLabel}
            <span className="sr-only"> — {title}</span>
            <ArrowRight size={12} aria-hidden="true" />
          </Link>
        ) : null}
      </div>
      {children}
    </section>
  );
}
