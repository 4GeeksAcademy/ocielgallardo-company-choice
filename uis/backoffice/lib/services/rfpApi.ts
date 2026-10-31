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
  | "waiting_for_approval"
  | "done"
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
  | "waiting_for_approval"
  | "done"
  | string;

export type RfpApprovalDecision =
  | "approved"
  | "rejected"
  | "request_changes";

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
  approval_status?: string | null;
  approver?: string | null;
  approved_at?: string | null;
  approval_round?: number;
}

export interface RfpFinalDocument {
  id?: number | null;
  ticket_id: string;
  sections: Record<string, unknown>;
  currency: string;
  generated_at: string;
  content_markdown: string;
}

export interface RfpTraceEvent {
  ts?: string;
  agent?: string;
  action?: string;
  department_id?: string | null;
  detail?: unknown;
  input?: unknown;
  output?: unknown;
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
  trace_events?: RfpTraceEvent[];
  final_document_id?: number | null;
  final_document?: RfpFinalDocument | null;
  conflicts?: unknown[];
  created_at: string;
  updated_at: string;
  metadata?: RfpMetadata | null;
  departments: DepartmentSection[];
  pipeline_stage: RfpPipelineStage;
  can_retry: boolean;
  can_start_draft?: boolean;
  can_start_approval?: boolean;
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

export function startRfpApproval(ticketId: string): Promise<RfpTicketCreated> {
  return healthcoreRequest<RfpTicketCreated>(
    `/rfp/tickets/${ticketId}/approval/start`,
    { method: "POST" },
  );
}

export function decideRfpApproval(
  ticketId: string,
  departmentId: string,
  decision: RfpApprovalDecision,
  note?: string,
): Promise<RfpTicketDetail> {
  return healthcoreRequest<RfpTicketDetail>(
    `/rfp/tickets/${ticketId}/approval/${departmentId}`,
    {
      method: "POST",
      body: JSON.stringify({ decision, note: note || null }),
    },
  );
}

export function friendlyRfpError(err: unknown, fallback: string): string {
  if (!(err instanceof HealthcoreApiError)) {
    return fallback;
  }
  if (err.status >= 500) {
    return "The RFP service is unavailable. Please try again.";
  }
  const raw = (err.message || "").trim();
  const lower = raw.toLowerCase();
  if (lower.includes("no open interrupt")) {
    return (
      "This decision is not ready yet. Use “Retry approvals” to " +
      "restart the flow and try again."
    );
  }
  if (lower.includes("already in progress")) {
    return "Approvals for this ticket are already in progress.";
  }
  if (lower.includes("not waiting for department approval")) {
    return "This ticket is not waiting for a department approval.";
  }
  if (
    lower.includes("failed to start approval") ||
    lower.includes("could not start the approval")
  ) {
    return "Could not start the approval review. Please try again.";
  }
  // Prefer short API messages; hide LangGraph dump (pending=[] next=[]).
  if (lower.includes("pending=") || lower.includes("department_id=")) {
    return (
      "Could not record the decision. Retry the approvals and try again; " +
      "if the problem continues, contact support."
    );
  }
  return raw || fallback;
}

/** Soften stored last_error strings before showing them in the ticket panel. */
export function friendlyRfpLastError(message: string | null | undefined): string {
  if (!message) return "";
  const lower = message.toLowerCase();
  if (lower.includes("no open interrupt")) {
    return (
      "This department's review is not available on the server. " +
      "Use “Retry approvals” and decide again."
    );
  }
  if (lower.includes("failed to start approval graph")) {
    return "Could not start the approval flow. Please try again.";
  }
  if (lower.includes("pending=") || /department_id=/.test(message)) {
    return (
      "A technical problem occurred while recording the decision. " +
      "Retry the approvals."
    );
  }
  return message;
}

export function formatReadability(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A (short document or metric not computable)";
  }
  return String(Math.round(value * 10) / 10);
}
