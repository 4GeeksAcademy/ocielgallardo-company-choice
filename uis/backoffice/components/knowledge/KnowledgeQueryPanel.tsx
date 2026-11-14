"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Square, TriangleAlert, User } from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  createAgentChatSocket,
  type ChatMessageView,
  type ChatWsStatus,
} from "@/lib/services/agentChatWs";
import { clearSessionAndRedirectToLogin } from "@/lib/services/healthcoreClient";
import {
  MIN_WORKING_MS,
  classifyAssistantText,
  connectionBadge,
  suggestionFor,
  type BubbleKind,
} from "@/components/knowledge/chatPresentation";

// Quick replies the agent already interprets via its memory-pending
// classification step. They only send text — the UI holds no memory logic.
const APPROVE_REPLY = "Yes, save that for next time.";
const REJECT_REPLY = "No, don't store that.";
const CORRECT_HINT = "Actually, the correct fact is: ";

function textHasMemoryProposal(text: string): boolean {
  const lowered = text.toLowerCase();
  return (
    lowered.includes("remember this for next time") ||
    lowered.includes("recuerde esto para la próxima vez")
  );
}

interface ChatItem {
  id: string;
  role: "user" | "assistant";
  text: string;
  kind: BubbleKind;
  /** "interrupted" | "stopped" | "complete" … (assistant only). */
  status?: string;
  /** Question to resend from a warning/error bubble. */
  retryQuestion?: string;
}

let itemSeq = 0;
function nextId(prefix: string): string {
  itemSeq += 1;
  return `${prefix}-${itemSeq}`;
}

function fromSnapshot(msgs: ChatMessageView[]): ChatItem[] {
  let lastUser = "";
  return msgs.map((m, idx) => {
    const role = m.role === "assistant" ? "assistant" : "user";
    const text = m.text || "";
    if (role === "user") lastUser = text;
    const kind: BubbleKind =
      role === "assistant" ? classifyAssistantText(text) : "normal";
    return {
      id: m.message_id || `snap-${idx}`,
      role,
      text,
      kind,
      status: m.status,
      retryQuestion: kind === "normal" ? undefined : lastUser || undefined,
    };
  });
}

function ConnectionIndicator({
  status,
  sessionId,
}: {
  status: ChatWsStatus;
  sessionId: string | null;
}) {
  const badge = connectionBadge(status);
  return (
    <div className="flex items-center gap-2 text-xs" role="status" aria-live="polite">
      <span className="relative flex h-2.5 w-2.5">
        {badge.pulse ? (
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 motion-reduce:animate-none ${badge.dotClass}`}
          />
        ) : null}
        <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${badge.dotClass}`} />
      </span>
      <span className={`font-medium ${badge.textClass}`}>{badge.label}</span>
      {sessionId ? (
        <span
          className="hidden font-mono text-slate-400 sm:inline dark:text-slate-500"
          title={`Session ${sessionId}`}
        >
          · {sessionId.slice(0, 8)}
        </span>
      ) : null}
    </div>
  );
}

function Avatar({ role }: { role: "user" | "assistant" }) {
  return (
    <span
      aria-hidden="true"
      className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
        role === "user"
          ? "bg-blue-600 text-white"
          : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100"
      }`}
    >
      {role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
    </span>
  );
}

function bubbleClass(role: "user" | "assistant", kind: BubbleKind): string {
  if (role === "user") {
    return "rounded-2xl rounded-tr-sm bg-blue-600 text-white";
  }
  if (kind === "warning") {
    return "rounded-2xl rounded-tl-sm border border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100";
  }
  if (kind === "error") {
    return "rounded-2xl rounded-tl-sm border border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100";
  }
  return "rounded-2xl rounded-tl-sm bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-50";
}

function ChatBubble({
  item,
  onRetry,
  retryDisabled,
}: {
  item: ChatItem;
  onRetry: (question: string) => void;
  retryDisabled: boolean;
}) {
  const isUser = item.role === "user";
  const flagged = item.kind !== "normal";
  return (
    <li className={`flex items-start gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
      <Avatar role={item.role} />
      <div className={`flex max-w-[85%] flex-col ${isUser ? "items-end" : "items-start"}`}>
        <span className="mb-0.5 text-[11px] font-medium text-slate-500 dark:text-slate-400">
          {isUser ? "You" : "Assistant"}
          {item.status === "interrupted" ? " · interrupted" : ""}
          {item.status === "stopped" ? " · stopped" : ""}
        </span>
        <div className={`px-3.5 py-2 text-sm leading-relaxed ${bubbleClass(item.role, item.kind)}`}>
          {flagged ? (
            <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold">
              <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
              {item.kind === "error" ? "Something went wrong" : "Could not complete this"}
            </p>
          ) : null}
          <p className="whitespace-pre-wrap break-words">{item.text}</p>
          {flagged ? (
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-current/20 pt-2 text-xs">
              <span>{suggestionFor(item.kind, item.text)}</span>
              {item.retryQuestion ? (
                <button
                  type="button"
                  onClick={() => onRetry(item.retryQuestion as string)}
                  disabled={retryDisabled}
                  className="rounded-md border border-current/40 px-2 py-0.5 font-semibold hover:bg-black/5 disabled:opacity-50 dark:hover:bg-white/10"
                >
                  Try again
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function WorkingIndicator() {
  return (
    <li className="flex items-start gap-2" aria-live="polite">
      <Avatar role="assistant" />
      <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-slate-100 px-3.5 py-2.5 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-300">
        <span className="flex gap-1" aria-hidden="true">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 motion-reduce:animate-none dark:bg-slate-500"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </span>
        <span>Working…</span>
      </div>
    </li>
  );
}

export function KnowledgeQueryPanel() {
  const [question, setQuestion] = useState("");
  const [items, setItems] = useState<ChatItem[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [generating, setGenerating] = useState(false);
  const [minElapsed, setMinElapsed] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<ChatWsStatus>("connecting");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [memoryProposalPending, setMemoryProposalPending] = useState(false);
  const [correcting, setCorrecting] = useState(false);

  const socketRef = useRef<ReturnType<typeof createAgentChatSocket> | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  // Per-turn bookkeeping read from socket callbacks (registered once).
  const streamingRef = useRef("");
  const minElapsedRef = useRef(true);
  const workingTimerRef = useRef<number | null>(null);
  const pendingFinishRef = useRef<(() => void) | null>(null);
  const ignoreRef = useRef(false);
  const lastQuestionRef = useRef("");

  function clearWorkingTimer() {
    if (workingTimerRef.current != null) {
      window.clearTimeout(workingTimerRef.current);
      workingTimerRef.current = null;
    }
  }

  function resetTurn() {
    clearWorkingTimer();
    pendingFinishRef.current = null;
    streamingRef.current = "";
    minElapsedRef.current = true;
    setMinElapsed(true);
    setStreamingText("");
    setGenerating(false);
  }

  // Run ``finish`` now, or once the minimum "Working…" time has passed.
  function finishWhenReady(finish: () => void) {
    if (minElapsedRef.current) {
      finish();
    } else {
      pendingFinishRef.current = finish;
    }
  }

  useEffect(() => {
    const stored =
      typeof window !== "undefined"
        ? window.sessionStorage.getItem("healthcore_chat_session_id")
        : null;

    const api = createAgentChatSocket({
      sessionId: stored,
      handlers: {
        onStatus: setWsStatus,
        onSnapshot: (sid, msgs) => {
          setSessionId(sid);
          window.sessionStorage.setItem("healthcore_chat_session_id", sid);
          setItems(fromSnapshot(msgs));
          ignoreRef.current = false;
          resetTurn();
          const lastAssistant = [...msgs]
            .reverse()
            .find((m) => m.role === "assistant" && m.status !== "interrupted");
          setMemoryProposalPending(
            Boolean(lastAssistant && textHasMemoryProposal(lastAssistant.text || ""))
          );
          setCorrecting(false);
        },
        // Everything after the server echo belongs to the new turn.
        onUserMessageEcho: () => {
          ignoreRef.current = false;
        },
        onToken: (token) => {
          if (ignoreRef.current) return;
          streamingRef.current += token;
          if (minElapsedRef.current) {
            setStreamingText(streamingRef.current);
          }
        },
        onGenerationCompleted: (_messageId, pending) => {
          if (ignoreRef.current) {
            ignoreRef.current = false;
            return;
          }
          const text = streamingRef.current;
          const retryQuestion = lastQuestionRef.current;
          finishWhenReady(() => {
            if (text) {
              const kind = classifyAssistantText(text);
              setItems((prev) => [
                ...prev,
                {
                  id: nextId("a"),
                  role: "assistant",
                  text,
                  kind,
                  status: "complete",
                  retryQuestion: kind === "normal" ? undefined : retryQuestion,
                },
              ]);
            }
            resetTurn();
            setMemoryProposalPending(Boolean(pending) || textHasMemoryProposal(text));
            setCorrecting(false);
          });
        },
        onGenerationInterrupted: () => {
          if (ignoreRef.current) {
            ignoreRef.current = false;
            return;
          }
          // Not requested by the user: the run failed server-side.
          const text = streamingRef.current;
          const retryQuestion = lastQuestionRef.current;
          finishWhenReady(() => {
            setItems((prev) => [
              ...prev,
              {
                id: nextId("e"),
                role: "assistant",
                text: text || "The answer could not be completed.",
                kind: "error",
                status: text ? "interrupted" : undefined,
                retryQuestion,
              },
            ]);
            resetTurn();
            setMemoryProposalPending(false);
            setCorrecting(false);
          });
        },
      },
    });
    socketRef.current = api;
    return () => {
      api.close();
      socketRef.current = null;
      if (workingTimerRef.current != null) {
        window.clearTimeout(workingTimerRef.current);
      }
    };
    // Socket handlers only touch refs and state setters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the newest message in view.
  useEffect(() => {
    const list = listRef.current;
    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [items, streamingText, generating, minElapsed]);

  function sendChatMessage(text: string) {
    setError(null);
    setItems((prev) => [...prev, { id: nextId("u"), role: "user", text, kind: "normal" }]);
    lastQuestionRef.current = text;
    clearWorkingTimer();
    pendingFinishRef.current = null;
    streamingRef.current = "";
    setStreamingText("");
    setGenerating(true);
    minElapsedRef.current = false;
    setMinElapsed(false);
    workingTimerRef.current = window.setTimeout(() => {
      workingTimerRef.current = null;
      minElapsedRef.current = true;
      setMinElapsed(true);
      setStreamingText(streamingRef.current);
      const finish = pendingFinishRef.current;
      pendingFinishRef.current = null;
      finish?.();
    }, MIN_WORKING_MS);
    setMemoryProposalPending(false);
    setCorrecting(false);
    socketRef.current?.sendUserMessage(text);
  }

  function trySend(text: string) {
    const trimmed = text.trim();
    if (trimmed.length === 0 || generating) {
      return;
    }
    if (wsStatus !== "connected") {
      setError("Chat is not connected yet. Wait a moment and try again.");
      return;
    }
    setQuestion("");
    sendChatMessage(trimmed);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    trySend(question);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      trySend(question);
    }
  }

  function handleStop() {
    if (!generating) return;
    const visible = minElapsed ? streamingRef.current : "";
    if (pendingFinishRef.current) {
      // The run already ended; just drop the held answer.
      pendingFinishRef.current = null;
    } else {
      // Ignore the rest of this run until the server confirms it ended.
      ignoreRef.current = true;
      socketRef.current?.sendStop();
    }
    setItems((prev) => [
      ...prev,
      {
        id: nextId("s"),
        role: "assistant",
        text: visible || "Stopped.",
        kind: "normal",
        status: "stopped",
      },
    ]);
    resetTurn();
    setMemoryProposalPending(false);
    setCorrecting(false);
  }

  if (wsStatus === "forbidden") {
    return (
      <div
        role="alert"
        className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100"
      >
        <p className="font-semibold">You don&apos;t have access to Knowledge.</p>
        <p className="mt-1">Ask an admin or manager to grant you access.</p>
      </div>
    );
  }

  if (wsStatus === "unauthorized") {
    return (
      <div
        role="alert"
        className="space-y-3 rounded-md border border-slate-300 bg-slate-50 p-4 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-50"
      >
        <p className="font-semibold">Your session has expired. Please sign in again.</p>
        <Button type="button" onClick={clearSessionAndRedirectToLogin}>
          Sign in
        </Button>
      </div>
    );
  }

  const showWorking = generating && (!minElapsed || !streamingText);
  const showStreaming = generating && minElapsed && Boolean(streamingText);

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 sm:p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2 dark:border-slate-700">
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
          Compliance assistant
          <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
            HIPAA / UK GDPR policies, tickets and stock
          </span>
        </p>
        <ConnectionIndicator status={wsStatus} sessionId={sessionId} />
      </div>

      <ul
        ref={listRef}
        className="flex max-h-[28rem] min-h-48 flex-col gap-3 overflow-y-auto px-1 py-2"
        aria-label="Conversation"
      >
        {items.length === 0 && !generating ? (
          <li className="m-auto text-center text-sm text-slate-500 dark:text-slate-400">
            Ask about clinic policies, ticket status, or inventory stock.
          </li>
        ) : null}
        {items.map((item) => (
          <ChatBubble
            key={item.id}
            item={item}
            onRetry={trySend}
            retryDisabled={generating || wsStatus !== "connected"}
          />
        ))}
        {showStreaming ? (
          <ChatBubble
            item={{ id: "streaming", role: "assistant", text: streamingText, kind: "normal" }}
            onRetry={trySend}
            retryDisabled
          />
        ) : null}
        {showWorking ? <WorkingIndicator /> : null}
      </ul>

      {memoryProposalPending && !generating && !correcting ? (
        <div className="space-y-2 rounded-md border border-slate-200 p-3 dark:border-slate-700">
          <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
            The agent asked whether to remember something. Quick reply:
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => trySend(APPROVE_REPLY)}>
              Yes, remember it
            </Button>
            <Button type="button" variant="secondary" onClick={() => trySend(REJECT_REPLY)}>
              No, don&apos;t store it
            </Button>
            <Button type="button" variant="ghost" onClick={() => setCorrecting(true)}>
              Correct it
            </Button>
          </div>
        </div>
      ) : null}

      {memoryProposalPending && correcting ? (
        <div className="space-y-2 rounded-md border border-slate-200 p-3 dark:border-slate-700">
          <label
            htmlFor="memory-correction"
            className="block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Type the correct fact and send — the agent will store your version instead.
          </label>
          <textarea
            id="memory-correction"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={2}
            maxLength={1000}
            placeholder={CORRECT_HINT}
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50 dark:placeholder:text-slate-500"
            autoFocus
          />
          <div className="flex gap-2">
            <Button
              type="button"
              onClick={() => trySend(question)}
              disabled={question.trim().length === 0 || generating}
            >
              Send correction
            </Button>
            <Button type="button" variant="ghost" onClick={() => setCorrecting(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      {!correcting ? (
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <label htmlFor="knowledge-question" className="sr-only">
            Ask about clinic policies, ticket status, or inventory stock
          </label>
          <textarea
            id="knowledge-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            maxLength={1000}
            placeholder="Ask a question… (Enter to send, Shift+Enter for a new line)"
            className="min-h-[2.75rem] flex-1 resize-y rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-50 dark:placeholder:text-slate-500"
          />
          {generating ? (
            <button
              type="button"
              onClick={handleStop}
              className="inline-flex items-center gap-1.5 rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
            >
              <Square className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={question.trim().length === 0}
              className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Send
            </button>
          )}
        </form>
      ) : null}

      {error ? (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      ) : null}
    </div>
  );
}
