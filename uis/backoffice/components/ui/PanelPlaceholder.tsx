interface PanelPlaceholderProps {
  minHeight?: number | string;
  label?: string;
}

export function PanelPlaceholder({
  minHeight = 320,
  label = "Loading panel…",
}: PanelPlaceholderProps) {
  return (
    <div
      aria-busy="true"
      className="animate-pulse rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 sm:p-6"
      style={{ minHeight }}
    >
      {label}
    </div>
  );
}
