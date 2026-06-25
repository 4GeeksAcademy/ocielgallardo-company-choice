export type ApplicationStatus =
  | "received"
  | "in_progress"
  | "selected"
  | "discarded";

export type ApplicationStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export interface Note {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
}

export interface Application {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: ApplicationStatus;
  stage: ApplicationStage;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
  notes?: Note[];
}

export interface RecordsListResponse {
  total: number;
  page: number;
  limit: number;
  data: Application[];
}

export interface NotesListResponse {
  data: Note[];
  meta: { total: number };
}

export interface RecordCreateInput {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url?: string | null;
  cv_url?: string | null;
  experience_years: number;
}

export interface RecordPatchInput {
  status?: ApplicationStatus;
  stage?: ApplicationStage;
}
