"use client";

import { useEffect, useRef, useState } from "react";
import {
  createAgentChatSocket,
  type ChatMessageView,
  type ChatWsStatus,
} from "@/lib/services/agentChatWs";

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
    default:
      return status;
  }
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
        },
        onToken: (token) => {
          setGenerating(true);
          streamingRef.current += token;
          setStreamingText(streamingRef.current);
        },
        onGenerationCompleted: () => {
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
        },
      },
    });
    socketRef.current = api;
    return () => {
      api.close();
      socketRef.current = null;
    };
  }, []);

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
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuestion("");
    streamingRef.current = "";
    setStreamingText("");
    setGenerating(true);
    socketRef.current?.sendUserMessage(trimmed);
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
    streamingRef.current = "";
    setStreamingText("");
    socketRef.current?.sendInterrupt(redirect);
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

      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
