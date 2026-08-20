export type IncidentStatus =
  | "open"
  | "in_progress"
  | "resolved"
  | "discarded";

export type IncidentOrigin = "customer" | "branch" | "internal";

export type IncidentCategory =
  | "clinical_equipment"
  | "it_system"
  | "billing_error"
  | "compliance_breach"
  | "patient_experience"
  | "staff_issue"
  | "facility_issue"
  | "referral_issue"
  | "other";

export type IncidentBranch =
  | "central"
  | "austin_north"
  | "dallas_uptown"
  | "houston_med_center"
  | "san_antonio_west"
  | "miami_brickell"
  | "miami_doral"
  | "orlando_east"
  | "tampa_bay"
  | "atlanta_midtown"
  | "savannah"
  | "london_city"
  | "london_west"
  | "manchester_central";

export interface ManagedIncident {
  id: number;
  title: string;
  description: string;
  category: IncidentCategory;
  status: IncidentStatus;
  origin: IncidentOrigin;
  branch: IncidentBranch;
  created_at: string;
  updated_at: string;
}

export interface IncidentCreateInput {
  title: string;
  description: string;
  category: IncidentCategory;
  origin: IncidentOrigin;
  branch: IncidentBranch;
  status?: IncidentStatus;
}

export interface IncidentStatusUpdateInput {
  status: IncidentStatus;
}

export interface IncidentSummary {
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
  total: number;
}

export interface IncidentListFilters {
  status?: IncidentStatus | "";
  origin?: IncidentOrigin | "";
  branch?: IncidentBranch | "";
  category?: IncidentCategory | "";
}

export const INCIDENT_STATUS_OPTIONS: { value: IncidentStatus; label: string }[] =
  [
    { value: "open", label: "Open" },
    { value: "in_progress", label: "In progress" },
    { value: "resolved", label: "Resolved" },
    { value: "discarded", label: "Discarded" },
  ];

export const INCIDENT_ORIGIN_OPTIONS: { value: IncidentOrigin; label: string }[] =
  [
    { value: "customer", label: "Customer" },
    { value: "branch", label: "Branch" },
    { value: "internal", label: "Internal" },
  ];

export const INCIDENT_CATEGORY_OPTIONS: {
  value: IncidentCategory;
  label: string;
}[] = [
  { value: "clinical_equipment", label: "Clinical equipment" },
  { value: "it_system", label: "IT system" },
  { value: "billing_error", label: "Billing error" },
  { value: "compliance_breach", label: "Compliance breach" },
  { value: "patient_experience", label: "Patient experience" },
  { value: "staff_issue", label: "Staff issue" },
  { value: "facility_issue", label: "Facility issue" },
  { value: "referral_issue", label: "Referral issue" },
  { value: "other", label: "Other" },
];

export const INCIDENT_BRANCH_OPTIONS: { value: IncidentBranch; label: string }[] =
  [
    { value: "central", label: "Central — Austin Main Clinic" },
    { value: "austin_north", label: "Austin — North" },
    { value: "dallas_uptown", label: "Dallas Uptown" },
    { value: "houston_med_center", label: "Houston Medical Center" },
    { value: "san_antonio_west", label: "San Antonio West" },
    { value: "miami_brickell", label: "Miami Brickell" },
    { value: "miami_doral", label: "Miami Doral" },
    { value: "orlando_east", label: "Orlando East" },
    { value: "tampa_bay", label: "Tampa Bay" },
    { value: "atlanta_midtown", label: "Atlanta Midtown" },
    { value: "savannah", label: "Savannah" },
    { value: "london_city", label: "London City" },
    { value: "london_west", label: "London West End" },
    { value: "manchester_central", label: "Manchester Central" },
  ];

export const STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["in_progress", "discarded"],
  in_progress: ["resolved", "discarded"],
  resolved: [],
  discarded: [],
};

export function branchLabel(branch: string): string {
  return (
    INCIDENT_BRANCH_OPTIONS.find((option) => option.value === branch)?.label ??
    branch
  );
}

export function categoryLabel(category: string): string {
  return (
    INCIDENT_CATEGORY_OPTIONS.find((option) => option.value === category)
      ?.label ?? category
  );
}

export function statusLabel(status: string): string {
  return (
    INCIDENT_STATUS_OPTIONS.find((option) => option.value === status)?.label ??
    status
  );
}

export function originLabel(origin: string): string {
  return (
    INCIDENT_ORIGIN_OPTIONS.find((option) => option.value === origin)?.label ??
    origin
  );
}
