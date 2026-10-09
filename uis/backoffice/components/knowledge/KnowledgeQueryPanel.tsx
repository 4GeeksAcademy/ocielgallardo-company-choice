"use client";

import { useState } from "react";
import { healthcoreRequest } from "@/lib/services/healthcoreClient";

interface KnowledgeQueryResponse {
  question: string;
  answer: string;
}

export function KnowledgeQueryPanel() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<KnowledgeQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3 || loading) {
      return;
    }
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await healthcoreRequest<KnowledgeQueryResponse>(
        "/knowledge/query",
        {
          method: "POST",
          body: JSON.stringify({ question: trimmed }),
        }
      );
      setAnswer(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="space-y-3">
        <label
          htmlFor="knowledge-question"
          className="block text-sm font-medium text-slate-700 dark:text-slate-200"
        >
          Ask about clinic policies, coverage, referrals, or first visits
        </label>
        <textarea
          id="knowledge-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          maxLength={1000}
          placeholder="e.g. Is there a charge for cancelling 12 hours in advance?"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-50"
        />
        <button
          type="submit"
          disabled={question.trim().length < 3 || loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>

      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      {loading && (
        <p aria-live="polite" className="text-sm text-slate-500 dark:text-slate-400">
          Searching clinic policies…
        </p>
      )}

      {answer && (
        <div className="space-y-3 rounded-md border border-slate-200 p-4 dark:border-slate-700">
          <p className="text-sm text-slate-900 dark:text-slate-50">
            {answer.answer}
          </p>
        </div>
      )}
    </div>
  );
}
