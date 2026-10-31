import { TONE_BG, type Tone } from "@/components/dashboard/tones";

export interface StackedBarSegment {
  label: string;
  value: number;
  tone: Tone;
}

interface StackedBarProps {
  segments: StackedBarSegment[];
  /** Accessible description, e.g. "Supplies by stock level". Values are appended. */
  label: string;
  showLegend?: boolean;
}

/** Single horizontal bar split into proportional segments. */
export function StackedBar({ segments, label, showLegend = true }: StackedBarProps) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const ariaLabel = `${label}: ${segments.map((s) => `${s.label} ${s.value}`).join(", ") || "no data"}`;

  return (
    <div>
      <div role="img" aria-label={ariaLabel} className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        {total > 0
          ? segments.map((segment) =>
              segment.value > 0 ? (
                <div
                  key={segment.label}
                  className={`h-full ${TONE_BG[segment.tone]}`}
                  style={{ width: `${(segment.value / total) * 100}%` }}
                />
              ) : null,
            )
          : null}
      </div>
      {showLegend ? (
        <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-300" aria-hidden="true">
          {segments.map((segment) => (
            <li key={segment.label} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${TONE_BG[segment.tone]}`} />
              {segment.label}
              <span className="font-semibold tabular-nums text-slate-900 dark:text-slate-50">{segment.value}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
