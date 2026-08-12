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
import { friendlyApiError } from "@/lib/utils/friendlyApiError";

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
  return friendlyApiError(err, fallback);
}
