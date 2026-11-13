/**
 * Pure presentation helpers for the Knowledge chat (no React, no I/O).
 */

import type { ChatWsStatus } from "@/lib/services/agentChatWs";

/** The "Working…" indicator stays up at least this long per turn. */
export const MIN_WORKING_MS = 3000;

export type BubbleKind = "normal" | "warning" | "error";

export interface ConnectionBadge {
  label: string;
  dotClass: string;
  textClass: string;
  pulse: boolean;
}

export function connectionBadge(status: ChatWsStatus): ConnectionBadge {
  switch (status) {
    case "connected":
      return {
        label: "Connected",
        dotClass: "bg-emerald-500",
        textClass: "text-emerald-700 dark:text-emerald-300",
        pulse: false,
      };
    case "connecting":
      return {
        label: "Connecting…",
        dotClass: "bg-amber-500",
        textClass: "text-amber-700 dark:text-amber-300",
        pulse: true,
      };
    case "reconnecting":
      return {
        label: "Reconnecting…",
        dotClass: "bg-amber-500",
        textClass: "text-amber-700 dark:text-amber-300",
        pulse: true,
      };
    case "unauthorized":
      return {
        label: "Session expired",
        dotClass: "bg-red-500",
        textClass: "text-red-700 dark:text-red-300",
        pulse: false,
      };
    case "forbidden":
      return {
        label: "No access",
        dotClass: "bg-red-500",
        textClass: "text-red-700 dark:text-red-300",
        pulse: false,
      };
    case "disconnected":
    default:
      return {
        label: "Offline",
        dotClass: "bg-slate-400",
        textClass: "text-slate-600 dark:text-slate-400",
        pulse: false,
      };
  }
}

// Fixed fallback/failure answers produced by the agent tools
// (data/pipelines/agent_tools.py). Matching is case-insensitive.
const NEEDS_DETAIL_MARKERS = [
  "which ticket do you mean",
  "which product do you mean",
];
const TOOL_FAILURE_MARKERS = [
  "i could not confirm the status of that ticket",
  "i could not confirm inventory stock",
  "credentials were rejected",
  "i could not find that ticket",
  "i could not find that product",
];

/** Classify an assistant answer: tool fallbacks become warning bubbles. */
export function classifyAssistantText(text: string): BubbleKind {
  const lowered = (text || "").toLowerCase();
  if (
    NEEDS_DETAIL_MARKERS.some((m) => lowered.includes(m)) ||
    TOOL_FAILURE_MARKERS.some((m) => lowered.includes(m))
  ) {
    return "warning";
  }
  return "normal";
}

/** Suggestion shown under a warning/error bubble. */
export function suggestionFor(kind: BubbleKind, text: string): string {
  const lowered = (text || "").toLowerCase();
  if (NEEDS_DETAIL_MARKERS.some((m) => lowered.includes(m))) {
    return "Add the ticket number or product name and send it again.";
  }
  if (lowered.includes("could not find")) {
    return "Check the ticket number, SKU or product name, or rephrase your question.";
  }
  if (kind === "error") {
    return "Something went wrong while answering. Try again or rephrase your question.";
  }
  return "Live data is unavailable right now. Try again in a moment or rephrase your question.";
}
