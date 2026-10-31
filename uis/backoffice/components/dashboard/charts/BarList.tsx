import { TONE_BG, type Tone } from "@/components/dashboard/tones";

export interface BarListItem {
  label: string;
  value: number;
  tone?: Tone;
}

interface BarListProps {
  items: BarListItem[];
  /** Accessible name of the list, e.g. "Incidents by branch". */
  label: string;
  formatValue?: (value: number) => string;
}

/** Horizontal bar list. Plain HTML/CSS so labels and values stay readable by assistive tech. */
export function BarList({ items, label, formatValue = (value) => value.toLocaleString("en-US") }: BarListProps) {
  const max = Math.max(1, ...items.map((item) => item.value));

  return (
    <ul aria-label={label} className="space-y-2.5">
      {items.map((item) => (
        <li key={item.label} className="text-sm">
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="truncate text-slate-700 dark:text-slate-200">{item.label}</span>
            <span className="shrink-0 font-semibold tabular-nums text-slate-900 dark:text-slate-50">
              {formatValue(item.value)}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden="true">
            <div
              className={`h-full rounded-full ${TONE_BG[item.tone ?? "primary"]}`}
              style={{ width: `${Math.max(2, (item.value / max) * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
