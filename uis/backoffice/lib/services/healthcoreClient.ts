function statusMessageEs(status: number): string {
  if (status >= 500) {
    return "Algo salió mal en el servidor. Inténtalo de nuevo en un momento.";
  }
  if (status === 404) {
    return "No se encontró el recurso solicitado.";
  }
  if (status === 401 || status === 403) {
    return "Tu sesión expiró. Vuelve a iniciar sesión.";
  }
  if (status === 409) {
    return "Este registro ya existe o entra en conflicto con datos existentes.";
  }
  if (status === 400 || status === 422) {
    return "Algunos datos enviados no son válidos. Revísalos e inténtalo de nuevo.";
  }
  return "No se pudo completar la solicitud. Inténtalo de nuevo.";
}

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
            : typeof item === "object" && item && "message" in item
              ? String((item as { message: unknown }).message)
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

function networkError(): HealthcoreApiError {
  return new HealthcoreApiError(
    "No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.",
    0
  );
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

  let response: Response;
  try {
    response = await fetch(`${HEALTHCORE_API_BASE_URL}${path}`, {
      ...rest,
      headers,
    });
  } catch {
    throw networkError();
  }

  if (response.status === 401 && auth) {
    clearSessionAndRedirectToLogin();
    throw new HealthcoreApiError("Sesión expirada o no válida.", 401);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type");
  let body: unknown = null;
  if (contentType?.includes("application/json")) {
    try {
      body = await response.json();
    } catch {
      throw new HealthcoreApiError(
        statusMessageEs(response.status),
        response.status
      );
    }
  }

  if (!response.ok) {
    throw new HealthcoreApiError(
      statusMessageEs(response.status),
      response.status,
      body
    );
  }

  return body as T;
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

  let response: Response;
  try {
    response = await fetch(`${HEALTHCORE_API_BASE_URL}${path}`, {
      ...rest,
      headers,
    });
  } catch {
    throw networkError();
  }

  if (response.status === 401 && auth) {
    clearSessionAndRedirectToLogin();
    throw new HealthcoreApiError("Sesión expirada o no válida.", 401);
  }

  if (!response.ok) {
    let details: unknown;
    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      try {
        details = await response.json();
      } catch {
        details = undefined;
      }
    }
    throw new HealthcoreApiError(
      statusMessageEs(response.status),
      response.status,
      details
    );
  }

  return response.blob();
}
