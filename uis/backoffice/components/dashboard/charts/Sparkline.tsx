import { TONE_TEXT, type Tone } from "@/components/dashboard/tones";

interface SparklineProps {
  values: number[];
  /** Accessible description, e.g. "Events per day, last 7 days". Values are appended. */
  label: string;
  tone?: Tone;
  className?: string;
}

const WIDTH = 100;
const HEIGHT = 28;
const PAD = 2;

/** Minimal SVG trend line with a soft area fill. No dependencies. */
export function Sparkline({ values, label, tone = "primary", className = "h-8 w-full" }: SparklineProps) {
  const ariaLabel = `${label}: ${values.length ? values.join(", ") : "no data"}`;

  if (values.length < 2) {
    return (
      <svg role="img" aria-label={ariaLabel} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className={`${className} ${TONE_TEXT.neutral}`} preserveAspectRatio="none">
        <line x1={0} x2={WIDTH} y1={HEIGHT / 2} y2={HEIGHT / 2} stroke="currentColor" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
      </svg>
    );
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const step = WIDTH / (values.length - 1);
  const points = values.map((value, index) => {
    const x = index * step;
    const y = HEIGHT - PAD - ((value - min) / range) * (HEIGHT - PAD * 2);
    return [x, y] as const;
  });
  const line = points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
  const area = `0,${HEIGHT} ${line} ${WIDTH},${HEIGHT}`;

  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="none"
      className={`${className} ${TONE_TEXT[tone]}`}
    >
      <polygon points={area} fill="currentColor" fillOpacity={0.12} />
      <polyline
        points={line}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
