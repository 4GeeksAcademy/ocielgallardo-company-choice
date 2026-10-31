import Link from "next/link";
import type { ReactNode } from "react";
import type { AsyncStatus } from "@/types/async";
import { CardState } from "@/components/dashboard/DashboardCard";
import { TONE_BADGE, type Tone } from "@/components/dashboard/tones";

interface KpiCardProps {
  label: string;
  href: string;
  status: AsyncStatus;
  error?: string | null;
  onRetry?: () => void;
  value?: string;
  unit?: string;
  badge?: { text: string; tone: Tone };
  /** Short supporting line under the number. */
  detail?: ReactNode;
  /** Small chart (sparkline, donut, stacked bar). */
  chart?: ReactNode;
}

/** KPI tile: uppercase label, big number, optional badge, detail and mini chart. */
export function KpiCard({ label, href, status, error, onRetry, value, unit, badge, detail, chart }: KpiCardProps) {
  return (
    <section className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <Link
            href={href}
            className="rounded hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            {label}
          </Link>
        </h3>
        {badge && status === "success" ? (
          <span className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${TONE_BADGE[badge.tone]}`}>
            {badge.text}
          </span>
        ) : null}
      </div>
      <div className="mt-3 flex-1">
        <CardState status={status} error={error} onRetry={onRetry} minHeight={72}>
          <p className="flex items-baseline gap-1.5">
            <span className="text-3xl font-bold tabular-nums text-slate-900 dark:text-slate-50">{value ?? "—"}</span>
            {unit ? <span className="text-sm text-slate-500 dark:text-slate-400">{unit}</span> : null}
          </p>
          {detail ? <div className="mt-1 text-xs text-slate-600 dark:text-slate-300">{detail}</div> : null}
          {chart ? <div className="mt-3">{chart}</div> : null}
        </CardState>
      </div>
    </section>
  );
}
