"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { healthcoreRequest } from "@/lib/services/healthcoreClient";

interface KnowledgeQueryResponse {
  question: string;
  answer: string;
  memory_proposal_pending?: boolean;
}

// Quick replies the agent already interprets via its memory-pending
// classification step. They only send text — the UI holds no memory logic.
const APPROVE_REPLY = "Yes, save that for next time.";
const REJECT_REPLY = "No, don't store that.";
const CORRECT_HINT = "Actually, the correct fact is: ";

export function KnowledgeQueryPanel() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<KnowledgeQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [correcting, setCorrecting] = useState(false);

  async function ask(rawQuestion: string) {
    setLoading(true);
    setError(null);
    setAnswer(null);
    setCorrecting(false);
    try {
      // Support agent (Part 2): the compiled LangGraph auto-routes each
      // question to clinic policies (RAG), live tickets, or live stock.
      const result = await healthcoreRequest<KnowledgeQueryResponse>(
        "/agent/query",
        {
          method: "POST",
          body: JSON.stringify({ question: rawQuestion }),
        }
      );
      setAnswer(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3 || loading) {
      return;
    }
    setQuestion("");
    await ask(trimmed);
  }

  async function handleMemoryDecision(reply: string) {
    if (loading) {
      return;
    }
    await ask(reply);
  }

  function handleCorrect() {
    setCorrecting(true);
  }

  const proposalPending = Boolean(answer?.memory_proposal_pending);

  return (
    <div className="space-y-4">
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
          placeholder="e.g. Is there a charge for cancelling 12 hours in advance? What is the status of ticket 2? Do we have stock of HCR-PPE-001?"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50"
        />
        <Button
          type="submit"
          disabled={question.trim().length < 3 || loading}
        >
          {loading ? "Asking…" : "Ask"}
        </Button>
      </form>

      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      {loading && (
        <p aria-live="polite" className="text-sm text-slate-500 dark:text-slate-400">
          Asking the support agent…
        </p>
      )}

      {answer && (
        <div className="space-y-3 rounded-md border border-slate-200 p-4 dark:border-slate-700">
          <p className="text-sm text-slate-900 dark:text-slate-50">
            {answer.answer}
          </p>

          {proposalPending && !loading && !correcting && (
            <div className="space-y-2 border-t border-slate-200 pt-3 dark:border-slate-700">
              <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
                The agent asked whether to remember something. Quick reply:
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  onClick={() => handleMemoryDecision(APPROVE_REPLY)}
                  disabled={loading}
                >
                  Yes, remember it
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => handleMemoryDecision(REJECT_REPLY)}
                  disabled={loading}
                >
                  No, don&apos;t store it
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleCorrect}
                  disabled={loading}
                >
                  Correct it
                </Button>
              </div>
            </div>
          )}

          {proposalPending && correcting && (
            <div className="space-y-2 border-t border-slate-200 pt-3 dark:border-slate-700">
              <label
                htmlFor="memory-correction"
                className="block text-xs font-medium text-slate-600 dark:text-slate-300"
              >
                Type the correct fact and send — the agent will store your
                version instead.
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
                  disabled={question.trim().length < 3 || loading}
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
          )}
        </div>
      )}
    </div>
  );
}
