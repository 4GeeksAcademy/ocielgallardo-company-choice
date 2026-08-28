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
      className="animate-pulse rounded-2xl border border-slate-200 bg-slate-100 p-4 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400"
      style={{ minHeight }}
    >
      {label}
    </div>
  );
}
