const HEALTHCORE_API_BASE_URL =
  process.env.NEXT_PUBLIC_HEALTHCORE_API_URL ?? "http://127.0.0.1:8000";

export const AUTH_TOKEN_KEY = "healthcore_access_token";

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

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function redirectToLogin(): void {
  if (typeof window === "undefined") {
    return;
  }
  const path = window.location.pathname;
  if (
    path === "/login" ||
    path === "/register" ||
    path === "/forgot-password" ||
    path === "/reset-password"
  ) {
    return;
  }
  window.location.assign("/login");
}

export function clearSessionAndRedirectToLogin(): void {
  clearAccessToken();
  redirectToLogin();
}

export function extractDetail(body: unknown, fallback: string): string {
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

export function getFieldErrors(
  body: unknown
): Record<string, string> | undefined {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return undefined;
  }
  const detail = (body as { detail: unknown }).detail;
  if (!Array.isArray(detail)) {
    return undefined;
  }

  const errors: Record<string, string> = {};
  for (const item of detail) {
    if (typeof item !== "object" || !item) {
      continue;
    }

    // FastAPI / our API: { field, message }
    if ("field" in item && "message" in item) {
      const field = String((item as { field: unknown }).field ?? "");
      if (field) {
        errors[field] = String((item as { message: unknown }).message);
      }
      continue;
    }

    // Pydantic-style: { loc, msg }
    if (
      "loc" in item &&
      "msg" in item &&
      Array.isArray((item as { loc: unknown }).loc)
    ) {
      const loc = (item as { loc: unknown[] }).loc;
      const field = String(loc[loc.length - 1] ?? "");
      if (field) {
        errors[field] = String((item as { msg: unknown }).msg);
      }
    }
  }
  return Object.keys(errors).length > 0 ? errors : undefined;
}

interface HealthcoreRequestOptions extends RequestInit {
  /** When false, do not attach Bearer token (login/register). Default true. */
  auth?: boolean;
  /** When false, skip JSON Content-Type (e.g. FormData). Default true. */
  json?: boolean;
}

export async function healthcoreRequest<T>(
  path: string,
  options: HealthcoreRequestOptions = {}
): Promise<T> {
  const { auth = true, json = true, headers: initHeaders, ...rest } = options;
  const headers = new Headers(initHeaders);

  if (json && !headers.has("Content-Type") && rest.body) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = getAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const startMs = performance.now();
  const response = await fetch(`${HEALTHCORE_API_BASE_URL}${path}`, {
    ...rest,
    headers,
  });
  const durationMs = Math.round(performance.now() - startMs);
  const httpMethod = (rest.method ?? "GET").toUpperCase();

  // Lazy import avoids circular dep (telemetry → healthcoreClient)
  if (typeof window !== "undefined" && !path.startsWith("/telemetry")) {
    void import("@/lib/services/telemetry").then(({ track }) => {
      track("api_latency_recorded", {
        path,
        method: httpMethod,
        duration_ms: durationMs,
        http_status: response.status,
      });
    });
  }

  if (response.status === 401 && auth) {
    if (typeof window !== "undefined") {
      void import("@/lib/services/telemetry").then(({ track }) => {
        track("session_expired", {
          path: window.location.pathname,
          app: "backoffice",
          idle_ms: 0,
        });
      });
    }
    clearSessionAndRedirectToLogin();
    throw new HealthcoreApiError("Sesión expirada o no válida.", 401);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type");
  const body = contentType?.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    detectDirectStockEditRejected(path, rest, response.status);
    throw new HealthcoreApiError(
      extractDetail(body, `Error ${response.status}`),
      response.status,
      body
    );
  }

  return body as T;
}

/**
 * Emit `direct_stock_edit_rejected` when a PUT/PATCH to an inventory product
 * route is rejected and the body tried to set `current_stock`.
 * Uses dynamic import to avoid circular dependency (telemetry → healthcoreClient).
 */
function detectDirectStockEditRejected(
  path: string,
  opts: RequestInit,
  status: number
): void {
  const method = (opts.method ?? "GET").toUpperCase();
  if (
    (method === "PUT" || method === "PATCH") &&
    /^\/inventory\/products/.test(path) &&
    typeof opts.body === "string"
  ) {
    try {
      const parsed = JSON.parse(opts.body);
      if ("current_stock" in parsed || "stock" in parsed) {
        void import("@/lib/services/telemetry").then(({ track }) => {
          track("direct_stock_edit_rejected", {
            attempted_path: path,
            http_status: status,
            rejection_reason: "direct_stock_field_in_body",
          });
        });
      }
    } catch {
      // body not JSON — skip
    }
  }
}

export async function healthcoreRequestBlob(
  path: string,
  options: HealthcoreRequestOptions = {}
): Promise<Blob> {
  const { auth = true, headers: initHeaders, ...rest } = options;
  const headers = new Headers(initHeaders);

  if (auth) {
    const token = getAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${HEALTHCORE_API_BASE_URL}${path}`, {
    ...rest,
    headers,
  });

  if (response.status === 401 && auth) {
    clearSessionAndRedirectToLogin();
    throw new HealthcoreApiError("Sesión expirada o no válida.", 401);
  }

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      const body = await response.json();
      detail = extractDetail(body, detail);
    }
    throw new HealthcoreApiError(detail, response.status);
  }

  return response.blob();
}
