import {
  HealthcoreApiError,
  healthcoreRequest,
} from "@/lib/services/healthcoreClient";
import type { MonthlyClinicSupplyPerformance } from "@/types/reporting";

export { HealthcoreApiError };

/**
 * Fetch the Monthly Clinic Supply Performance KPIs for one month.
 *
 * Bearer-authenticated (default `auth: true`) because it exposes business KPIs.
 * When `monthStart` is omitted, the API returns the most recent computed month.
 */
export async function fetchMonthlyClinicSupplyPerformance(params?: {
  monthStart?: string;
}): Promise<MonthlyClinicSupplyPerformance> {
  const query = new URLSearchParams();
  if (params?.monthStart) {
    query.set("month_start", params.monthStart);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return healthcoreRequest<MonthlyClinicSupplyPerformance>(
    `/reporting/monthly-clinic-supply-performance${suffix}`,
    { method: "GET" }
  );
}

export function friendlyReportingError(err: unknown, fallback: string): string {
  if (err instanceof HealthcoreApiError) {
    return err.message || fallback;
  }
  if (err instanceof Error) {
    return err.message || fallback;
  }
  return fallback;
}
