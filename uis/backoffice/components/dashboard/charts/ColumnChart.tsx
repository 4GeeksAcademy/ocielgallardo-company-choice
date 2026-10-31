import { TONE_TEXT, type Tone } from "@/components/dashboard/tones";

export interface ColumnSeries {
  label: string;
  tone: Tone;
  values: number[];
}

interface ColumnChartProps {
  /** X-axis labels, one per column group. */
  categories: string[];
  series: ColumnSeries[];
  /** Accessible description, e.g. "Inventory orders per day". */
  label: string;
  height?: number;
}

const WIDTH = 280;
const AXIS = 14;

/** Grouped column chart in plain SVG; a visually hidden table carries the values. */
export function ColumnChart({ categories, series, label, height = 120 }: ColumnChartProps) {
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const plotHeight = height - AXIS;
  const groupWidth = WIDTH / Math.max(1, categories.length);
  const barWidth = Math.max(2, (groupWidth * 0.7) / Math.max(1, series.length));
  const labelEvery = Math.ceil(categories.length / 7);

  return (
    <figure>
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="h-auto w-full" aria-hidden="true">
        <line x1={0} x2={WIDTH} y1={plotHeight} y2={plotHeight} className="stroke-slate-200 dark:stroke-slate-700" />
        {categories.map((category, groupIndex) => {
          const groupX = groupIndex * groupWidth + groupWidth * 0.15;
          return (
            <g key={category}>
              {series.map((s, seriesIndex) => {
                const value = s.values[groupIndex] ?? 0;
                const barHeight = (value / max) * (plotHeight - 4);
                return (
                  <rect
                    key={s.label}
                    x={groupX + seriesIndex * barWidth}
                    y={plotHeight - barHeight}
                    width={barWidth - 1}
                    height={barHeight}
                    rx={1}
                    fill="currentColor"
                    className={TONE_TEXT[s.tone]}
                  />
                );
              })}
              {groupIndex % labelEvery === 0 ? (
                <text
                  x={groupIndex * groupWidth + groupWidth / 2}
                  y={height - 2}
                  textAnchor="middle"
                  className="fill-slate-500 text-[8px] dark:fill-slate-400"
                >
                  {category}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-3 text-xs text-slate-600 dark:text-slate-300">
        {series.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-sm ${TONE_TEXT[s.tone]} bg-current`} aria-hidden="true" />
            {s.label}
          </span>
        ))}
      </figcaption>
      <table className="sr-only">
        <caption>{label}</caption>
        <thead>
          <tr>
            <th scope="col">Day</th>
            {series.map((s) => (
              <th key={s.label} scope="col">
                {s.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {categories.map((category, index) => (
            <tr key={category}>
              <th scope="row">{category}</th>
              {series.map((s) => (
                <td key={s.label}>{s.values[index] ?? 0}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
