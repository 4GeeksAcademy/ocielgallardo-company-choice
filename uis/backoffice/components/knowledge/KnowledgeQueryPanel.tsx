"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  createAgentChatSocket,
  type ChatMessageView,
  type ChatWsStatus,
} from "@/lib/services/agentChatWs";
import { clearSessionAndRedirectToLogin } from "@/lib/services/healthcoreClient";

function statusLabel(status: ChatWsStatus): string {
  switch (status) {
    case "connected":
      return "Chat connected";
    case "connecting":
      return "Connecting chat…";
    case "reconnecting":
      return "Reconnecting chat…";
    case "disconnected":
      return "Chat disconnected";
    case "unauthorized":
      return "Session expired";
    case "forbidden":
      return "No access";
    default:
      return status;
  }
}

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

export function KnowledgeQueryPanel() {
  const [question, setQuestion] = useState("");
  const [interruptHint, setInterruptHint] = useState("");
  const [messages, setMessages] = useState<ChatMessageView[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<ChatWsStatus>("connecting");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [memoryProposalPending, setMemoryProposalPending] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const socketRef = useRef<ReturnType<typeof createAgentChatSocket> | null>(
    null
  );
  const streamingRef = useRef("");

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
          setMessages(
            msgs.map((m) => ({
              message_id: m.message_id,
              role: m.role === "assistant" ? "assistant" : "user",
              text: m.text || "",
              status: m.status,
            }))
          );
          setStreamingText("");
          streamingRef.current = "";
          setGenerating(false);
          const lastAssistant = [...msgs]
            .reverse()
            .find((m) => m.role === "assistant" && m.status !== "interrupted");
          setMemoryProposalPending(
            Boolean(lastAssistant && textHasMemoryProposal(lastAssistant.text || ""))
          );
          setCorrecting(false);
        },
        onToken: (token) => {
          setGenerating(true);
          streamingRef.current += token;
          setStreamingText(streamingRef.current);
        },
        onGenerationCompleted: (_messageId, pending) => {
          const text = streamingRef.current;
          if (text) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text, status: "complete" },
            ]);
          }
          streamingRef.current = "";
          setStreamingText("");
          setGenerating(false);
          setMemoryProposalPending(
            Boolean(pending) || textHasMemoryProposal(text)
          );
          setCorrecting(false);
        },
        onGenerationInterrupted: () => {
          const text = streamingRef.current;
          if (text) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", text, status: "interrupted" },
            ]);
          }
          streamingRef.current = "";
          setStreamingText("");
          setGenerating(false);
          setMemoryProposalPending(false);
          setCorrecting(false);
        },
      },
    });
    socketRef.current = api;
    return () => {
      api.close();
      socketRef.current = null;
    };
  }, []);

  function sendChatMessage(text: string) {
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text }]);
    streamingRef.current = "";
    setStreamingText("");
    setGenerating(true);
    setMemoryProposalPending(false);
    setCorrecting(false);
    socketRef.current?.sendUserMessage(text);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3 || generating) {
      return;
    }
    if (wsStatus !== "connected") {
      setError("Chat is not connected yet. Wait a moment and try again.");
      return;
    }
    setQuestion("");
    sendChatMessage(trimmed);
  }

  function handleInterrupt() {
    const redirect = interruptHint.trim() || question.trim();
    if (!redirect) {
      setError("Enter a redirect message before interrupting.");
      return;
    }
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: redirect }]);
    setInterruptHint("");
    setQuestion("");
    setGenerating(true);
    setMemoryProposalPending(false);
    setCorrecting(false);
    streamingRef.current = "";
    setStreamingText("");
    socketRef.current?.sendInterrupt(redirect);
  }

  function handleMemoryDecision(reply: string) {
    const trimmed = reply.trim();
    if (generating || trimmed.length < 3) {
      return;
    }
    if (wsStatus !== "connected") {
      setError("Chat is not connected yet. Wait a moment and try again.");
      return;
    }
    setQuestion("");
    sendChatMessage(trimmed);
  }

  if (wsStatus === "forbidden") {
    return (
      <div
        role="alert"
        className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100"
      >
        <p className="font-semibold">You don&apos;t have access to Knowledge.</p>
        <p className="mt-1">
          Ask an admin or manager to grant you access.
        </p>
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

  return (
    <div className="space-y-4">
      <p
        className={`text-xs ${
          wsStatus === "connected"
            ? "text-emerald-700 dark:text-emerald-300"
            : wsStatus === "reconnecting" || wsStatus === "connecting"
              ? "text-amber-700 dark:text-amber-300"
              : "text-slate-500"
        }`}
      >
        {statusLabel(wsStatus)}
        {sessionId ? (
          <span className="ml-2 font-mono text-slate-500">
            session {sessionId}
          </span>
        ) : null}
      </p>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Compliance assistant (staff only) — HIPAA / UK GDPR policy questions.
        Answers stream live; use Interrupt to redirect mid-reply.
      </p>

      <div className="max-h-80 space-y-3 overflow-y-auto rounded-md border border-slate-200 p-3 dark:border-slate-700">
        {messages.length === 0 && !streamingText ? (
          <p className="text-sm text-slate-500">No messages yet.</p>
        ) : null}
        {messages.map((m, idx) => (
          <div
            key={`${m.message_id || idx}-${m.role}`}
            className={`rounded px-3 py-2 text-sm ${
              m.role === "user"
                ? "bg-blue-50 text-slate-900 dark:bg-blue-950/40 dark:text-slate-50"
                : "bg-slate-50 text-slate-900 dark:bg-slate-800/60 dark:text-slate-50"
            }`}
          >
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {m.role}
              {m.status === "interrupted" ? " (interrupted)" : ""}
            </p>
            <p className="whitespace-pre-wrap">{m.text}</p>
          </div>
        ))}
        {streamingText ? (
          <div className="rounded bg-slate-50 px-3 py-2 text-sm text-slate-900 dark:bg-slate-800/60 dark:text-slate-50">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              assistant
            </p>
            <p className="whitespace-pre-wrap">{streamingText}</p>
          </div>
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <label
          htmlFor="knowledge-question"
          className="block text-sm font-medium text-slate-700 dark:text-slate-200"
        >
          Ask about clinic policies, ticket status, or inventory stock
        </label>
        <textarea
          id="knowledge-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          maxLength={1000}
          placeholder="e.g. What is allowed under UK GDPR for staff notes? Is there a charge for cancelling 12 hours in advance?"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50"
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={question.trim().length < 3 || generating}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {generating ? "Streaming…" : "Send"}
          </button>
        </div>
      </form>

      <div className="space-y-2 rounded-md border border-amber-200 bg-amber-50/50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
        <label
          htmlFor="interrupt-hint"
          className="block text-sm font-medium text-slate-700 dark:text-slate-200"
        >
          Interrupt & redirect (while streaming)
        </label>
        <input
          id="interrupt-hint"
          value={interruptHint}
          onChange={(e) => setInterruptHint(e.target.value)}
          placeholder="wait, my question was about UK GDPR, not HIPAA"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
        />
        <button
          type="button"
          onClick={handleInterrupt}
          disabled={!generating}
          className="rounded-md bg-amber-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Interrupt
        </button>
      </div>

      {memoryProposalPending && !generating && !correcting ? (
        <div className="space-y-2 rounded-md border border-slate-200 p-4 dark:border-slate-700">
          <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
            The agent asked whether to remember something. Quick reply:
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={() => handleMemoryDecision(APPROVE_REPLY)}
              disabled={generating}
            >
              Yes, remember it
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => handleMemoryDecision(REJECT_REPLY)}
              disabled={generating}
            >
              No, don&apos;t store it
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setCorrecting(true)}
              disabled={generating}
            >
              Correct it
            </Button>
          </div>
        </div>
      ) : null}

      {memoryProposalPending && correcting ? (
        <div className="space-y-2 rounded-md border border-slate-200 p-4 dark:border-slate-700">
          <label
            htmlFor="memory-correction"
            className="block text-xs font-medium text-slate-600 dark:text-slate-300"
          >
            Type the correct fact and send — the agent will store your version
            instead.
          </label>
          <textarea
            id="memory-correction"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={2}
            maxLength={1000}
            placeholder={CORRECT_HINT}
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50"
            autoFocus
          />
          <div className="flex gap-2">
            <Button
              type="button"
              onClick={() => handleMemoryDecision(question.trim())}
              disabled={question.trim().length < 3 || generating}
            >
              Send correction
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setCorrecting(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
