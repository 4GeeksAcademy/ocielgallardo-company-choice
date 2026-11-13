/**
 * Compliance assistant WebSocket client (BRIEFING Part 2).
 * Auth via ?token= (same JWT as backoffice). Reconnect with session_id.
 */

import {
  getAccessToken,
  HEALTHCORE_API_BASE_URL,
} from "@/lib/services/healthcoreClient";

export type ChatWsStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  /** 4401 (or no token): session missing/expired — terminal, no retry. */
  | "unauthorized"
  /** 4403: authenticated but not admin/manager — terminal, no retry. */
  | "forbidden";

/** Close codes sent by the backend (services/app/routers/agent.py). */
export const WS_CLOSE_UNAUTHORIZED = 4401;
export const WS_CLOSE_FORBIDDEN = 4403;

/** Terminal status for a close code, or null when a reconnect makes sense. */
export function terminalStatusForCloseCode(
  code: number
): "unauthorized" | "forbidden" | null {
  if (code === WS_CLOSE_UNAUTHORIZED) return "unauthorized";
  if (code === WS_CLOSE_FORBIDDEN) return "forbidden";
  return null;
}

export interface ChatMessageView {
  message_id?: string;
  role: "user" | "assistant";
  text: string;
  status?: string;
}

export type ChatWsServerEvent =
  | {
      event: "session_snapshot";
      data: { session_id: string; messages: ChatMessageView[] };
    }
  | {
      event: "token_chunk";
      data: { session_id: string; token: string; sequence: number };
    }
  | {
      event: "generation_completed";
      data: {
        session_id: string;
        message_id: string;
        memory_proposal_pending?: boolean;
      };
    }
  | {
      event: "generation_interrupted";
      data: {
        session_id: string;
        message_id: string;
        status: string;
      };
    }
  | {
      event: "user_message";
      data: { session_id: string; text: string };
    };

export interface AgentChatWsHandlers {
  onStatus?: (status: ChatWsStatus) => void;
  onSnapshot?: (sessionId: string, messages: ChatMessageView[]) => void;
  onToken?: (token: string, sequence: number) => void;
  onGenerationCompleted?: (
    messageId: string,
    memoryProposalPending?: boolean
  ) => void;
  onGenerationInterrupted?: (messageId: string) => void;
  onUserMessageEcho?: (text: string) => void;
}

function toWsBase(httpBase: string): string {
  if (httpBase.startsWith("https://")) {
    return `wss://${httpBase.slice("https://".length)}`;
  }
  if (httpBase.startsWith("http://")) {
    return `ws://${httpBase.slice("http://".length)}`;
  }
  return httpBase;
}

export function createAgentChatSocket(options: {
  sessionId?: string | null;
  handlers: AgentChatWsHandlers;
  baseDelayMs?: number;
  maxDelayMs?: number;
}): {
  close: () => void;
  sendUserMessage: (text: string) => void;
  sendInterrupt: (newInput: string) => void;
  sendStop: () => void;
  getSessionId: () => string | null;
} {
  const {
    handlers,
    baseDelayMs = 1000,
    maxDelayMs = 30_000,
  } = options;

  let sessionId: string | null = options.sessionId ?? null;
  let socket: WebSocket | null = null;
  let stopped = false;
  let attempt = 0;
  let reconnectTimer: number | null = null;

  const getSessionId = () => sessionId;

  const send = (event: string, data: Record<string, unknown>) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }
    socket.send(JSON.stringify({ event, data }));
  };

  const sendUserMessage = (text: string) => {
    if (!sessionId) return;
    send("user_message", { session_id: sessionId, text });
  };

  const sendInterrupt = (newInput: string) => {
    if (!sessionId) return;
    send("interrupt_requested", {
      session_id: sessionId,
      new_input: newInput,
    });
  };

  /**
   * Cancel the generation in flight. Reuses the backend `interrupt_requested`
   * event with an empty `new_input`: the server cancels the run, keeps the
   * partial text and emits `generation_interrupted` (no new turn is started).
   */
  const sendStop = () => sendInterrupt("");

  const connect = () => {
    if (stopped) return;
    const token = getAccessToken();
    if (!token) {
      stopped = true;
      handlers.onStatus?.("unauthorized");
      return;
    }
    handlers.onStatus?.(attempt > 0 ? "reconnecting" : "connecting");
    const params = new URLSearchParams({ token });
    if (sessionId) {
      params.set("session_id", sessionId);
    }
    const url = `${toWsBase(HEALTHCORE_API_BASE_URL)}/agent/chat/ws?${params}`;
    const ws = new WebSocket(url);
    socket = ws;

    ws.onopen = () => {
      attempt = 0;
      handlers.onStatus?.("connected");
    };

    ws.onmessage = (ev) => {
      let parsed: ChatWsServerEvent;
      try {
        parsed = JSON.parse(String(ev.data)) as ChatWsServerEvent;
      } catch {
        return;
      }
      switch (parsed.event) {
        case "session_snapshot":
          sessionId = parsed.data.session_id;
          handlers.onSnapshot?.(
            parsed.data.session_id,
            parsed.data.messages || []
          );
          break;
        case "token_chunk":
          handlers.onToken?.(parsed.data.token, parsed.data.sequence);
          break;
        case "generation_completed":
          handlers.onGenerationCompleted?.(
            parsed.data.message_id,
            parsed.data.memory_proposal_pending
          );
          break;
        case "generation_interrupted":
          handlers.onGenerationInterrupted?.(parsed.data.message_id);
          break;
        case "user_message":
          handlers.onUserMessageEcho?.(parsed.data.text);
          break;
        default:
          break;
      }
    };

    ws.onclose = (ev) => {
      socket = null;
      if (stopped) {
        handlers.onStatus?.("disconnected");
        return;
      }
      // Auth/role rejections are final: retrying would loop forever.
      const terminal = terminalStatusForCloseCode(ev.code);
      if (terminal) {
        stopped = true;
        handlers.onStatus?.(terminal);
        return;
      }
      handlers.onStatus?.("reconnecting");
      const delay = Math.min(
        maxDelayMs,
        baseDelayMs * 2 ** Math.min(attempt, 5)
      );
      attempt += 1;
      reconnectTimer = window.setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  };

  connect();

  return {
    close: () => {
      const alreadyStopped = stopped;
      stopped = true;
      if (reconnectTimer != null) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
      // Keep a terminal unauthorized/forbidden status visible.
      if (!alreadyStopped) {
        handlers.onStatus?.("disconnected");
      }
    },
    sendUserMessage,
    sendInterrupt,
    sendStop,
    getSessionId,
  };
}
