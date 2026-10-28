import {
  HealthcoreApiError,
  healthcoreRequest,
} from "@/lib/services/healthcoreClient";

export { HealthcoreApiError as RfpApiError };

export type RfpTicketStatus =
  | "analyzing"
  | "discarded"
  | "intake_complete"
  | "drafting"
  | "under_evaluation"
  | "needs_human_review"
  | string;

export type RfpPipelineStage =
  | "converting"
  | "agents"
  | "synthesizing"
  | "failed"
  | "discarded"
  | "complete"
  | "drafting"
  | "under_evaluation"
  | "draft_ready"
  | "needs_human_review"
  | string;

export interface RfpTicketSummary {
  ticket_id: string;
  status: RfpTicketStatus;
  created_at: string;
  updated_at: string;
  original_filename?: string | null;
  client_name?: string | null;
  ready_for_part2: boolean;
  ready_for_part3?: boolean;
}

export interface DepartmentSection {
  department_id: string;
  owner: string;
  key_aspects: unknown[];
  open_questions: unknown[];
  contains_phi: boolean;
  draft_content?: string | null;
  evaluation_results?: Record<string, unknown>;
  iteration_count?: number;
  needs_human_review?: boolean;
}

export interface RfpMetadata {
  client_name?: string | null;
  client_country?: string | null;
  program_type?: string | null;
  covered_population?: string | null;
  deadline?: string | null;
  budget_range?: string | null;
  departments_needed?: unknown[];
  flesch_kincaid_grade?: number | null;
  gunning_fog?: number | null;
  flesch_reading_ease?: number | null;
  readability_metrics?: Record<string, unknown>;
  contains_phi: boolean;
  original_filename?: string | null;
}

export interface RfpTicketDetail {
  ticket_id: string;
  rfp_id?: string | null;
  status: RfpTicketStatus;
  raw_pdf_path: string;
  markdown_path?: string | null;
  last_error?: string | null;
  discard_reason?: string | null;
  ready_for_part2: boolean;
  ready_for_part3?: boolean;
  handoff_payload: Record<string, unknown>;
  part2_handoff_payload?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  metadata?: RfpMetadata | null;
  departments: DepartmentSection[];
  pipeline_stage: RfpPipelineStage;
  can_retry: boolean;
  can_start_draft?: boolean;
}

export interface RfpTicketCreated {
  ticket_id: string;
  status: RfpTicketStatus;
  celery_task_id?: string | null;
}

export function listRfpTickets(): Promise<RfpTicketSummary[]> {
  return healthcoreRequest<RfpTicketSummary[]>("/rfp/tickets");
}

export function getRfpTicket(ticketId: string): Promise<RfpTicketDetail> {
  return healthcoreRequest<RfpTicketDetail>(`/rfp/tickets/${ticketId}`);
}

export async function uploadRfpPdf(file: File): Promise<RfpTicketCreated> {
  const form = new FormData();
  form.append("file", file);
  return healthcoreRequest<RfpTicketCreated>("/rfp/tickets", {
    method: "POST",
    body: form,
    json: false,
  });
}

export function retryRfpTicket(ticketId: string): Promise<RfpTicketCreated> {
  return healthcoreRequest<RfpTicketCreated>(`/rfp/tickets/${ticketId}/retry`, {
    method: "POST",
  });
}

export function startRfpDraft(ticketId: string): Promise<RfpTicketCreated> {
  return healthcoreRequest<RfpTicketCreated>(
    `/rfp/tickets/${ticketId}/draft`,
    { method: "POST" },
  );
}

export function retryRfpDraft(ticketId: string): Promise<RfpTicketCreated> {
  return healthcoreRequest<RfpTicketCreated>(
    `/rfp/tickets/${ticketId}/draft/retry`,
    { method: "POST" },
  );
}

export function friendlyRfpError(err: unknown, fallback: string): string {
  if (!(err instanceof HealthcoreApiError)) {
    return fallback;
  }
  if (err.status >= 500) {
    return "El servicio de RFPs no está disponible. Intenta de nuevo.";
  }
  return err.message || fallback;
}

export function formatReadability(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A (documento corto o métrica no calculable)";
  }
  return String(Math.round(value * 10) / 10);
}
