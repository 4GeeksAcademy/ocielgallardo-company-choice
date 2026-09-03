/**
 * TelemetryService — single entry-point for all backoffice event capture.
 *
 * Every event flows through `track()`. Components never call fetch/axios
 * for telemetry directly.
 *
 * Mechanisms:
 *  - In-memory queue flushed every 10 s OR when 20 events accumulate.
 *  - `navigator.sendBeacon` on visibilitychange / beforeunload.
 *  - Exponential-backoff retry (1 s → 2 s → 4 s, max 3 attempts).
 *  - Endpoint read from NEXT_PUBLIC_TELEMETRY_ENDPOINT (env var).
 */

import { AUTH_TOKEN_KEY } from "@/lib/services/healthcoreClient";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const TELEMETRY_ENDPOINT =
  process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT ??
  "http://localhost:8000/telemetry/events";

const SCHEMA_VERSION = "1.0.0";
const BATCH_SIZE = 20;
/** Flush every 3s locally so DevTools shows batches quickly (plan default was 10s). */
const FLUSH_INTERVAL_MS = 3_000;
const MAX_RETRIES = 3;
const BASE_RETRY_MS = 1_000;

/* ------------------------------------------------------------------ */
/*  Session helpers                                                   */
/* ------------------------------------------------------------------ */

const SESSION_KEY = "healthcore_telemetry_session_id";

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "server";
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/** Extract `sub` (user id) from the JWT in localStorage without a library. */
function getUserId(): string {
  if (typeof window === "undefined") return "anonymous";
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (!token) return "anonymous";
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload));
    return String(decoded.sub ?? decoded.user_id ?? "anonymous");
  } catch {
    return "anonymous";
  }
}

/* ------------------------------------------------------------------ */
/*  Envelope builder                                                  */
/* ------------------------------------------------------------------ */

interface TelemetryEvent {
  eventId: string;
  timestamp: string;
  sessionId: string | null;
  userId: string;
  event_type: string;
  schemaVersion: string;
  requestId: string | null;
  properties: Record<string, unknown>;
}

function buildEnvelope(
  eventType: string,
  properties: Record<string, unknown>
): TelemetryEvent {
  return {
    eventId: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    sessionId: getOrCreateSessionId(),
    userId: getUserId(),
    event_type: eventType,
    schemaVersion: SCHEMA_VERSION,
    requestId: crypto.randomUUID(),
    properties,
  };
}

/* ------------------------------------------------------------------ */
/*  Queue + flush logic                                               */
/* ------------------------------------------------------------------ */

let queue: TelemetryEvent[] = [];
let flushTimer: ReturnType<typeof setInterval> | null = null;

function startTimer(): void {
  if (typeof window === "undefined") return;
  if (flushTimer) return;
  flushTimer = setInterval(() => {
    void flush();
  }, FLUSH_INTERVAL_MS);
}

function stopTimer(): void {
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
}

/** Send queued events via fetch with exponential-backoff retry. */
async function flush(): Promise<void> {
  if (queue.length === 0) return;

  const batch = [...queue];
  queue = [];

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const res = await fetch(TELEMETRY_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events: batch }),
      });
      if (res.ok) return; // success — done
    } catch {
      // network error — fall through to retry
    }
    // exponential backoff before next attempt
    if (attempt < MAX_RETRIES - 1) {
      await new Promise((r) => setTimeout(r, BASE_RETRY_MS * 2 ** attempt));
    }
  }
  // all retries failed — discard (telemetry is not critical)
}

/** Send remaining events via sendBeacon (reliable on page unload). */
function beaconFlush(): void {
  if (queue.length === 0) return;
  const payload = JSON.stringify({ events: queue });
  queue = [];
  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    navigator.sendBeacon(
      TELEMETRY_ENDPOINT,
      new Blob([payload], { type: "application/json" })
    );
  }
}

/* ------------------------------------------------------------------ */
/*  Lifecycle listeners                                               */
/* ------------------------------------------------------------------ */

let listenersAttached = false;

function attachListeners(): void {
  if (typeof window === "undefined" || listenersAttached) return;
  listenersAttached = true;

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      beaconFlush();
    }
  });

  window.addEventListener("beforeunload", () => {
    beaconFlush();
  });

  startTimer();
}

/* ------------------------------------------------------------------ */
/*  Public API                                                        */
/* ------------------------------------------------------------------ */

/**
 * Capture a telemetry event.
 *
 * @param eventType  — must match `event_type` from event-schemas.json
 * @param properties — only allowlisted keys; no PII / PHI
 *
 * @example
 * track("inbound_order_created", { clinic_id: 3, country: "US", product_id: 12, product_category: "ppe", quantity: 40 });
 */
export function track(
  eventType: string,
  properties: Record<string, unknown> = {}
): void {
  if (typeof window === "undefined") return; // SSR guard

  attachListeners();

  const event = buildEnvelope(eventType, properties);
  queue.push(event);

  if (queue.length >= BATCH_SIZE) {
    void flush();
  }
}
