import type { IncidentAnalysisSummary } from "@/types/incidents";
import {
  HealthcoreApiError,
  healthcoreRequest,
  healthcoreRequestBlob,
} from "@/lib/services/healthcoreClient";

export { HealthcoreApiError };

export async function analyzeIncidents(
  file: File
): Promise<IncidentAnalysisSummary> {
  const formData = new FormData();
  formData.append("file", file);

  return healthcoreRequest<IncidentAnalysisSummary>("/api/incidents/analyze", {
    method: "POST",
    json: false,
    body: formData,
  });
}

export async function exportIncidentsResults(): Promise<void> {
  const blob = await healthcoreRequestBlob("/api/incidents/results/export");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "results.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
