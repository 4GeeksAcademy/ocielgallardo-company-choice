import type { ApplicationStage, ApplicationStatus } from "@/types/application";

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  "received",
  "in_progress",
  "selected",
  "discarded",
];

export const APPLICATION_STAGES: ApplicationStage[] = [
  "pending",
  "review",
  "personal_interview",
  "technical_interview",
  "offer_presented",
];

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  received: "Recibida",
  in_progress: "En proceso",
  selected: "Seleccionada",
  discarded: "Descartada",
};

export const STAGE_LABELS: Record<ApplicationStage, string> = {
  pending: "Pendiente",
  review: "Revisión CV",
  personal_interview: "Entrevista personal",
  technical_interview: "Entrevista técnica",
  offer_presented: "Oferta presentada",
};

export const STATUS_BADGE_CLASSES: Record<ApplicationStatus, string> = {
  received: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 ring-slate-200 dark:ring-slate-600",
  in_progress: "bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 ring-blue-200 dark:ring-blue-800",
  selected: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 ring-emerald-200 dark:ring-emerald-800",
  discarded: "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 ring-red-200 dark:ring-red-800",
};

export const STAGE_BADGE_CLASSES: Record<ApplicationStage, string> = {
  pending: "bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 ring-amber-200 dark:ring-amber-800",
  review: "bg-cyan-50 dark:bg-cyan-950/40 text-cyan-800 dark:text-cyan-300 ring-cyan-200 dark:ring-cyan-800",
  personal_interview: "bg-violet-50 dark:bg-violet-950/40 text-violet-800 dark:text-violet-300 ring-violet-200 dark:ring-violet-800",
  technical_interview: "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-800 dark:text-indigo-300 ring-indigo-200 dark:ring-indigo-800",
  offer_presented: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 ring-emerald-200 dark:ring-emerald-800",
};
