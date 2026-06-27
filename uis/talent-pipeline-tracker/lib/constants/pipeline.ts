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
  received: "bg-slate-100 text-slate-700 ring-slate-200",
  in_progress: "bg-blue-50 text-blue-700 ring-blue-200",
  selected: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  discarded: "bg-red-50 text-red-700 ring-red-200",
};

export const STAGE_BADGE_CLASSES: Record<ApplicationStage, string> = {
  pending: "bg-amber-50 text-amber-800 ring-amber-200",
  review: "bg-cyan-50 text-cyan-800 ring-cyan-200",
  personal_interview: "bg-violet-50 text-violet-800 ring-violet-200",
  technical_interview: "bg-indigo-50 text-indigo-800 ring-indigo-200",
  offer_presented: "bg-emerald-50 text-emerald-800 ring-emerald-200",
};
