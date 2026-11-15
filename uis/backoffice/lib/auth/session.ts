/**
 * Pure session helpers (no DOM, no React, no imports) so they can be unit
 * tested with plain `node --test` (see session.test.mjs).
 *
 * The backoffice keeps the JWT in localStorage, so these helpers run in the
 * browser: the signature is NOT verified here (only the backend can do that),
 * we only read `exp` to stop showing protected UI once the token is stale.
 */

/** Routes reachable without a session. Everything else needs a valid token. */
export const PUBLIC_PATHS: ReadonlySet<string> = new Set([
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
]);

export const LOGIN_PATH = "/login";
export const HOME_PATH = "/";

/** `?reason=` value the login page turns into the "session expired" notice. */
export const SESSION_EXPIRED_REASON = "expired";
export const SESSION_EXPIRED_MESSAGE =
  "Your session expired, please sign in again.";

/** Treat a token as expired slightly early so requests do not race `exp`. */
export const DEFAULT_EXPIRY_SKEW_MS = 10_000;

export type SessionState = "valid" | "expired" | "none";

export function isPublicPath(pathname: string): boolean {
  const clean = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return PUBLIC_PATHS.has(clean);
}

function base64UrlDecode(segment: string): string | null {
  if (!/^[A-Za-z0-9_-]+={0,2}$/.test(segment)) {
    return null;
  }
  const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
  try {
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
}

/** Decode the JWT payload, or null when the token is not a well-formed JWT. */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length !== 3 || !parts[1]) {
    return null;
  }
  const json = base64UrlDecode(parts[1]);
  if (json === null) {
    return null;
  }
  try {
    const payload: unknown = JSON.parse(json);
    return payload && typeof payload === "object" && !Array.isArray(payload)
      ? (payload as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

/** `exp` in epoch milliseconds, or null when missing / malformed. */
export function getTokenExpiryMs(token: string): number | null {
  const payload = decodeJwtPayload(token);
  const exp = payload?.exp;
  if (typeof exp !== "number" || !Number.isFinite(exp)) {
    return null;
  }
  return exp * 1000;
}

/**
 * True when the token is unusable: malformed, without `exp`, or past `exp`
 * (minus `skewMs`). Backend tokens always carry `exp`, so a token without it
 * is treated as invalid rather than as "never expires".
 */
export function isTokenExpired(
  token: string,
  nowMs: number,
  skewMs: number = DEFAULT_EXPIRY_SKEW_MS
): boolean {
  const expiryMs = getTokenExpiryMs(token);
  if (expiryMs === null) {
    return true;
  }
  return nowMs >= expiryMs - skewMs;
}

export function getSessionState(
  token: string | null | undefined,
  nowMs: number,
  skewMs: number = DEFAULT_EXPIRY_SKEW_MS
): SessionState {
  if (!token) {
    return "none";
  }
  return isTokenExpired(token, nowMs, skewMs) ? "expired" : "valid";
}

const INTERNAL_ORIGIN = "http://healthcore.internal";

/**
 * Return `raw` only when it is a same-origin, in-app path; otherwise `fallback`.
 * Blocks open redirects (`//evil.com`, `/\evil.com`, `https://evil.com`,
 * `javascript:`) and never sends the user back to a public auth page.
 */
export function safeNextPath(
  raw: string | null | undefined,
  fallback: string = HOME_PATH
): string {
  if (typeof raw !== "string" || raw.length === 0 || raw.length > 2048) {
    return fallback;
  }
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) {
    return fallback;
  }
  // Control characters (tabs/newlines are stripped by URL parsers).
  for (let i = 0; i < raw.length; i += 1) {
    const code = raw.charCodeAt(i);
    if (code <= 0x1f || code === 0x7f) {
      return fallback;
    }
  }
  let url: URL;
  try {
    url = new URL(raw, INTERNAL_ORIGIN);
  } catch {
    return fallback;
  }
  if (url.origin !== INTERNAL_ORIGIN) {
    return fallback;
  }
  if (isPublicPath(url.pathname)) {
    return fallback;
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

/**
 * `/login?next=<current path>&reason=expired`. `next` is dropped when it is
 * the home page or not a safe internal path.
 */
export function buildLoginHref(
  currentPath: string | null | undefined,
  options: { expired?: boolean } = {}
): string {
  const params = new URLSearchParams();
  const next = safeNextPath(currentPath, "");
  if (next && next !== HOME_PATH) {
    params.set("next", next);
  }
  if (options.expired) {
    params.set("reason", SESSION_EXPIRED_REASON);
  }
  const query = params.toString();
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH;
}
