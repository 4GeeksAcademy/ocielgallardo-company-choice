import type {
  IncidentCreateInput,
  IncidentListFilters,
  IncidentStatusUpdateInput,
  IncidentSummary,
  ManagedIncident,
} from "@/types/incidentManager";
import {
  HealthcoreApiError,
  healthcoreRequest,
} from "@/lib/services/healthcoreClient";

export { HealthcoreApiError as IncidentManagerApiError };

function buildQuery(filters: IncidentListFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.origin) params.set("origin", filters.origin);
  if (filters.branch) params.set("branch", filters.branch);
  if (filters.category) params.set("category", filters.category);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function fetchIncidents(
  filters: IncidentListFilters = {}
): Promise<ManagedIncident[]> {
  return healthcoreRequest<ManagedIncident[]>(
    `/api/incidents${buildQuery(filters)}`
  );
}

export function fetchIncident(id: number): Promise<ManagedIncident> {
  return healthcoreRequest<ManagedIncident>(`/api/incidents/${id}`);
}

export function createIncident(
  input: IncidentCreateInput
): Promise<ManagedIncident> {
  return healthcoreRequest<ManagedIncident>("/api/incidents", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateIncidentStatus(
  id: number,
  input: IncidentStatusUpdateInput
): Promise<ManagedIncident> {
  return healthcoreRequest<ManagedIncident>(`/api/incidents/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function fetchIncidentSummary(): Promise<IncidentSummary> {
  return healthcoreRequest<IncidentSummary>("/api/incidents/summary");
}

export function friendlyIncidentError(err: unknown, fallback: string): string {
  if (!(err instanceof HealthcoreApiError)) {
    return fallback;
  }
  if (err.status >= 500) {
    return "Something went wrong on the server. Please try again in a moment.";
  }
  if (err.status === 404) {
    return "The requested incident was not found.";
  }
  if (err.status === 401 || err.status === 403) {
    return "Your session expired. Please sign in again.";
  }
  // Prefer first field message when present
  if (err.details && typeof err.details === "object" && "detail" in err.details) {
    const detail = (err.details as { detail: unknown }).detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
      const first = detail[0] as { message?: unknown; msg?: unknown };
      const message = first.message ?? first.msg;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
    if (typeof detail === "string" && detail.trim()) {
      // Avoid technical jargon for users
      if (/traceback|exception|stack/i.test(detail)) {
        return fallback;
      }
      return detail;
    }
  }
  if (/traceback|exception|stack/i.test(err.message)) {
    return fallback;
  }
  return err.message || fallback;
}
