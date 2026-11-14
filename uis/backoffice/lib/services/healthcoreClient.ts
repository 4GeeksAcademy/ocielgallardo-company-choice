import {
  buildLoginHref,
  getSessionState,
  isPublicPath,
  isTokenExpired,
  LOGIN_PATH,
  type SessionState,
} from "@/lib/auth/session";

export const HEALTHCORE_API_BASE_URL =
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

/** Raw token from localStorage (may be expired). Prefer `getValidAccessToken`. */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

/** The stored token when it is present and not past its `exp`; otherwise null. */
export function getValidAccessToken(): string | null {
  const token = getAccessToken();
  if (!token || isTokenExpired(token, Date.now())) {
    return null;
  }
  return token;
}

/** Current session state: "valid", "expired" (stale/malformed token) or "none". */
export function readSessionState(): SessionState {
  return getSessionState(getAccessToken(), Date.now());
}

/**
 * Fired on the window whenever this tab sets or clears the token. The native
 * `storage` event only reaches *other* tabs, so the auth guard listens to both.
 */
export const AUTH_CHANGE_EVENT = "healthcore:auth-change";

function notifyAuthChange(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
  }
}

export function setAccessToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  notifyAuthChange();
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_KEY);
  notifyAuthChange();
}

function currentPathWithQuery(): string {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

/**
 * Hard-navigate to `/login?next=<current route>`; with `expired` the login page
 * shows "Your session expired, please sign in again." No-op on public pages.
 */
export function redirectToLogin(options: { expired?: boolean } = {}): void {
  if (typeof window === "undefined") {
    return;
  }
  if (isPublicPath(window.location.pathname)) {
    return;
  }
  window.location.assign(buildLoginHref(currentPathWithQuery(), options));
}

/** Session expired or rejected (any 401): drop the token and go to login. */
export function clearSessionAndRedirectToLogin(): void {
  clearAccessToken();
  redirectToLogin({ expired: true });
}

/** Explicit logout: drop the token and go to a clean login page. */
export function signOut(): void {
  clearAccessToken();
  if (typeof window !== "undefined") {
    window.location.assign(LOGIN_PATH);
  }
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

const SESSION_EXPIRED_ERROR = "Session expired or invalid.";

/**
 * Token for an authenticated call. A missing or expired token never reaches
 * the API: the session is cleared and the user is sent to login right away.
 */
function requireValidToken(): string {
  const token = getValidAccessToken();
  if (!token) {
    clearSessionAndRedirectToLogin();
    throw new HealthcoreApiError(SESSION_EXPIRED_ERROR, 401);
  }
  return token;
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
    headers.set("Authorization", `Bearer ${requireValidToken()}`);
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
    throw new HealthcoreApiError(SESSION_EXPIRED_ERROR, 401);
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
    headers.set("Authorization", `Bearer ${requireValidToken()}`);
  }

  const response = await fetch(`${HEALTHCORE_API_BASE_URL}${path}`, {
    ...rest,
    headers,
  });

  if (response.status === 401 && auth) {
    clearSessionAndRedirectToLogin();
    throw new HealthcoreApiError(SESSION_EXPIRED_ERROR, 401);
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
