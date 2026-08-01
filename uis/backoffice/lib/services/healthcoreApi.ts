import type { IncidentAnalysisSummary } from "@/types/incidents";

const HEALTHCORE_API_BASE_URL =
  process.env.NEXT_PUBLIC_HEALTHCORE_API_URL ?? "http://127.0.0.1:8000";

export class HealthcoreApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "HealthcoreApiError";
  }
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item)
        )
        .join("; ");
    }
  }
  return fallback;
}

export async function analyzeIncidents(
  file: File
): Promise<IncidentAnalysisSummary> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${HEALTHCORE_API_BASE_URL}/api/incidents/analyze`,
    {
      method: "POST",
      body: formData,
    }
  );

  const contentType = response.headers.get("content-type");
  const body = contentType?.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw new HealthcoreApiError(
      extractDetail(body, `Error ${response.status}`),
      response.status,
      body
    );
  }

  return body as IncidentAnalysisSummary;
}

export async function exportIncidentsResults(): Promise<void> {
  const response = await fetch(
    `${HEALTHCORE_API_BASE_URL}/api/incidents/results/export`
  );

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      const body = await response.json();
      detail = extractDetail(body, detail);
    }
    throw new HealthcoreApiError(detail, response.status);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "results.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
