export type IncidentCategory =
  | "APPOINTMENT"
  | "BILLING"
  | "CLINICAL_CARE"
  | "ACCESSIBILITY"
  | "ADMINISTRATIVE";

export type IncidentStatus = "OPEN" | "CLOSED" | "DISCARDED";

export type IncidentCountry = "US" | "UK";

export type InvalidRuleKey =
  | "invalid_clinic_id"
  | "country_clinic_mismatch"
  | "invalid_category"
  | "empty_description"
  | "missing_patient_id"
  | "closed_without_score";

export interface CountPercentage {
  count: number;
  percentage: number;
}

export interface SatisfactionSummary {
  scored_cases: number;
  average: number | null;
  histogram: Record<number, number>;
}

export interface IncidentAnalysisSummary {
  total: number;
  valid: number;
  invalid: number;
  invalid_breakdown: Record<InvalidRuleKey, number>;
  by_category: Record<IncidentCategory, CountPercentage>;
  by_status: Record<IncidentStatus, CountPercentage>;
  by_country: Record<IncidentCountry, CountPercentage>;
  satisfaction: SatisfactionSummary;
}
