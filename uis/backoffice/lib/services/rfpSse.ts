/**
 * RFP SSE client (fetch + Bearer). EventSource cannot set Authorization.
 *
 * Recovery strategy (documented): refetch-then-SSE.
 * - Live events upsert by ticket_id (no full list fetch per event).
 * - After disconnect, exponential backoff reconnects the stream; the UI
 *   refetches GET /rfp/tickets once status returns to "connected" so tickets
 *   created while offline are not lost. Dedupe by ticket_id on merge.
 */

import {
  clearSessionAndRedirectToLogin,
  getAccessToken,
  HEALTHCORE_API_BASE_URL,
} from "@/lib/services/healthcoreClient";
import type { RfpTicketSummary } from "@/lib/services/rfpApi";

export type RfpSseConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

export interface RfpTicketCreatedEvent {
  ticket_id: string;
  rfp_id?: string | null;
  client_name?: string | null;
  client_country?: string | null;
  program_type?: string | null;
  status: string;
  created_at?: string | null;
}

export type RfpSseEvent =
  | { type: "rfp_ticket_created"; data: RfpTicketCreatedEvent }
  | { type: string; data: Record<string, unknown> };

export interface SubscribeRfpEventsOptions {
  onEvent: (event: RfpSseEvent) => void;
  onStatus?: (status: RfpSseConnectionStatus) => void;
  /** Fired when the stream becomes connected after a reconnect attempt. */
  onRecovered?: () => void;
  signal?: AbortSignal;
  /** Initial reconnect delay (ms). Doubles up to max. */
  baseDelayMs?: number;
  maxDelayMs?: number;
}

/**
 * Merge a live SSE ticket into the list without duplicates (key = ticket_id).
 * Prefers existing list fields when the event only carries a subset.
 */
export function upsertTicketFromSseEvent(
  tickets: RfpTicketSummary[],
  event: RfpTicketCreatedEvent
): RfpTicketSummary[] {
  const createdAt = event.created_at || new Date().toISOString();
  const idx = tickets.findIndex((t) => t.ticket_id === event.ticket_id);
  if (idx >= 0) {
    const prev = tickets[idx];
    const next = [...tickets];
    next[idx] = {
      ...prev,
      status: event.status || prev.status,
      client_name: event.client_name ?? prev.client_name,
      updated_at: createdAt,
    };
    return next;
  }
  return [
    {
      ticket_id: event.ticket_id,
      status: event.status,
      created_at: createdAt,
      updated_at: createdAt,
      client_name: event.client_name ?? null,
      ready_for_part2: false,
      ready_for_part3: false,
    },
    ...tickets,
  ];
}

/** Collapse a ticket list to unique ticket_id (first occurrence wins). */
export function dedupeTicketsById(
  tickets: RfpTicketSummary[]
): RfpTicketSummary[] {
  const seen = new Set<string>();
  const out: RfpTicketSummary[] = [];
  for (const row of tickets) {
    if (seen.has(row.ticket_id)) {
      continue;
    }
    seen.add(row.ticket_id);
    out.push(row);
  }
  return out;
}

function parseSseChunk(
  buffer: string
): { frames: Array<{ event: string; data: string }>; rest: string } {
  const frames: Array<{ event: string; data: string }> = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  for (const block of parts) {
    if (!block.trim() || block.trimStart().startsWith(":")) {
      continue;
    }
    let event = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    if (dataLines.length > 0) {
      frames.push({ event, data: dataLines.join("\n") });
    }
  }
  return { frames, rest };
}

async function openStreamOnce(
  signal: AbortSignal,
  onEvent: (event: RfpSseEvent) => void,
  onStatus?: (status: RfpSseConnectionStatus) => void,
  opts?: { recovering: boolean; onRecovered?: () => void }
): Promise<void> {
  const token = getAccessToken();
  if (!token) {
    clearSessionAndRedirectToLogin();
    throw new Error("Missing access token");
  }

  onStatus?.("connecting");
  const response = await fetch(
    `${HEALTHCORE_API_BASE_URL}/rfp/events/stream`,
    {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
        Authorization: `Bearer ${token}`,
      },
      signal,
      cache: "no-store",
    }
  );

  if (response.status === 401) {
    clearSessionAndRedirectToLogin();
    throw new Error("Unauthorized");
  }
  if (!response.ok || !response.body) {
    throw new Error(`SSE stream failed (${response.status})`);
  }

  onStatus?.("connected");
  if (opts?.recovering) {
    opts.onRecovered?.();
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseChunk(buffer);
    buffer = parsed.rest;
    for (const frame of parsed.frames) {
      let data: Record<string, unknown> = {};
      try {
        data = JSON.parse(frame.data) as Record<string, unknown>;
      } catch {
        continue;
      }
      if (frame.event === "rfp_ticket_created") {
        onEvent({
          type: "rfp_ticket_created",
          data: data as unknown as RfpTicketCreatedEvent,
        });
      } else {
        onEvent({ type: frame.event, data });
      }
    }
  }
}

/**
 * Subscribe to RFP SSE with exponential backoff reconnect until aborted.
 */
export function subscribeRfpEvents(
  options: SubscribeRfpEventsOptions
): () => void {
  const {
    onEvent,
    onStatus,
    onRecovered,
    signal: outerSignal,
    baseDelayMs = 1000,
    maxDelayMs = 30_000,
  } = options;

  const controller = new AbortController();
  const onOuterAbort = () => controller.abort();
  outerSignal?.addEventListener("abort", onOuterAbort);

  let stopped = false;
  let attempt = 0;
  let recovering = false;

  const run = async () => {
    while (!stopped && !controller.signal.aborted) {
      try {
        await openStreamOnce(controller.signal, onEvent, onStatus, {
          recovering,
          onRecovered,
        });
        recovering = false;
        attempt = 0;
        if (stopped || controller.signal.aborted) {
          break;
        }
        // Clean close — reconnect
        recovering = true;
        onStatus?.("reconnecting");
      } catch {
        if (stopped || controller.signal.aborted) {
          break;
        }
        recovering = true;
        onStatus?.("reconnecting");
        const delay = Math.min(
          maxDelayMs,
          baseDelayMs * 2 ** Math.min(attempt, 5)
        );
        attempt += 1;
        await new Promise<void>((resolve) => {
          const id = window.setTimeout(resolve, delay);
          const abortWait = () => {
            window.clearTimeout(id);
            resolve();
          };
          controller.signal.addEventListener("abort", abortWait, {
            once: true,
          });
        });
      }
    }
    if (!stopped) {
      onStatus?.("disconnected");
    }
  };

  void run();

  return () => {
    stopped = true;
    outerSignal?.removeEventListener("abort", onOuterAbort);
    controller.abort();
    onStatus?.("disconnected");
  };
}
