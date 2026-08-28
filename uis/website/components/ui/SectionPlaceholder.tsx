interface SectionPlaceholderProps {
  minHeight?: number | string;
  label?: string;
}

export function SectionPlaceholder({
  minHeight = 240,
  label = "Loading section…",
}: SectionPlaceholderProps) {
  return (
    <div
      aria-hidden="true"
      className="animate-pulse rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800/60"
      style={{ minHeight }}
    >
      <span className="sr-only">{label}</span>
    </div>
  );
}
