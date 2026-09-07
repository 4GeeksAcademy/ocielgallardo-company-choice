import {
  HealthcoreApiError,
  healthcoreRequest,
} from "@/lib/services/healthcoreClient";
import type { TelemetryReport } from "@/types/telemetry";

export { HealthcoreApiError };

export async function fetchTelemetryReport(params?: {
  startDate?: string;
  endDate?: string;
}): Promise<TelemetryReport> {
  const query = new URLSearchParams();
  if (params?.startDate) {
    query.set("start_date", params.startDate);
  }
  if (params?.endDate) {
    query.set("end_date", params.endDate);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return healthcoreRequest<TelemetryReport>(`/telemetry/report${suffix}`, {
    method: "GET",
    auth: false,
  });
}

export function friendlyTelemetryError(
  err: unknown,
  fallback: string
): string {
  if (err instanceof HealthcoreApiError) {
    return err.message || fallback;
  }
  if (err instanceof Error) {
    return err.message || fallback;
  }
  return fallback;
}
