/**
 * Types for the Monthly Clinic Supply Performance reporting dashboard.
 *
 * Mirrors the response of `GET /reporting/monthly-clinic-supply-performance`
 * (implemented in `services/reporting/`), which surfaces the four CONTEXT KPIs
 * from `reporting.monthly_clinic_supply_performance`.
 */

export type ClinicCountry = "US" | "UK";
export type ClinicCurrency = "USD" | "GBP";

export interface ClinicSupplyPerformanceRow {
  /** Clinic identifier, serialized as the text of an integer "1"–"12". */
  clinic_id: string;
  country: ClinicCountry | string;
  /** KPI — Supply Cost per Clinic (in the row's currency, never mixed). */
  total_supply_cost: number;
  /** KPI — Supply Consumption Volume. */
  supply_consumption_count: number;
  /** KPI — Critical Stockout Frequency. */
  critical_stockout_count: number;
  /** KPI — Expiry Risk Count. */
  expiry_risk_count: number;
  currency: ClinicCurrency | string;
}

export interface MonthlyClinicSupplyPerformance {
  /** First day of the reported month (ISO date), or null when no data exists. */
  month_start: string | null;
  clinics: ClinicSupplyPerformanceRow[];
}
