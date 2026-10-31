/** Shared colour tones for dashboard widgets (presentation only). */
export type Tone = "primary" | "success" | "warning" | "danger" | "info" | "neutral";

/** Text colour — used with `fill="currentColor"` / `stroke="currentColor"` in SVG. */
export const TONE_TEXT: Record<Tone, string> = {
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  info: "text-info",
  neutral: "text-slate-400 dark:text-slate-500",
};

export const TONE_BG: Record<Tone, string> = {
  primary: "bg-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
  neutral: "bg-slate-300 dark:bg-slate-600",
};

export const TONE_BADGE: Record<Tone, string> = {
  primary: "bg-blue-50 text-primary ring-blue-200 dark:bg-blue-950/50 dark:ring-blue-800",
  success: "bg-green-50 text-green-700 ring-green-200 dark:bg-green-950/40 dark:text-green-300 dark:ring-green-800",
  warning: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-800",
  danger: "bg-red-50 text-red-700 ring-red-200 dark:bg-red-950/40 dark:text-red-300 dark:ring-red-800",
  info: "bg-cyan-50 text-cyan-700 ring-cyan-200 dark:bg-cyan-950/40 dark:text-cyan-300 dark:ring-cyan-800",
  neutral: "bg-slate-50 text-slate-600 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
};
