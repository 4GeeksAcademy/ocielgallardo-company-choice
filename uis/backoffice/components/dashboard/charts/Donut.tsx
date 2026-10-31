import { TONE_BG, TONE_TEXT, type Tone } from "@/components/dashboard/tones";

export interface DonutSegment {
  label: string;
  value: number;
  tone: Tone;
}

interface DonutProps {
  segments: DonutSegment[];
  /** Accessible description, e.g. "Incidents by status". Segment values are appended. */
  label: string;
  size?: number;
  /** Optional big number in the centre. */
  centerValue?: string;
  showLegend?: boolean;
}

const RADIUS = 15.9155; // circumference ≈ 100 → dash lengths read as percentages
const STROKE = 3.6;

/** SVG donut built from stroked circles (no dependencies). */
export function Donut({ segments, label, size = 72, centerValue, showLegend = true }: DonutProps) {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const ariaLabel = `${label}: ${segments.map((s) => `${s.label} ${s.value}`).join(", ") || "no data"}`;
  let offset = 0;

  return (
    <div className="flex items-center gap-4">
      <svg role="img" aria-label={ariaLabel} viewBox="0 0 36 36" width={size} height={size} className="shrink-0 -rotate-90">
        <circle cx={18} cy={18} r={RADIUS} fill="none" strokeWidth={STROKE} className="stroke-slate-100 dark:stroke-slate-800" />
        {total > 0
          ? segments.map((segment) => {
              const length = (segment.value / total) * 100;
              const circle = (
                <circle
                  key={segment.label}
                  cx={18}
                  cy={18}
                  r={RADIUS}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={STROKE}
                  strokeDasharray={`${length} ${100 - length}`}
                  strokeDashoffset={-offset}
                  className={TONE_TEXT[segment.tone]}
                />
              );
              offset += length;
              return circle;
            })
          : null}
        {centerValue ? (
          <text
            x={18}
            y={18}
            textAnchor="middle"
            dominantBaseline="central"
            transform="rotate(90 18 18)"
            className="fill-slate-900 text-[9px] font-bold dark:fill-slate-50"
          >
            {centerValue}
          </text>
        ) : null}
      </svg>
      {showLegend ? (
        <ul className="min-w-0 space-y-1 text-xs" aria-hidden="true">
          {segments.map((segment) => (
            <li key={segment.label} className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
              <span className={`h-2 w-2 shrink-0 rounded-full ${TONE_BG[segment.tone]}`} />
              <span className="truncate">{segment.label}</span>
              <span className="ml-auto pl-2 font-semibold tabular-nums text-slate-900 dark:text-slate-50">
                {segment.value.toLocaleString("en-US")}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
