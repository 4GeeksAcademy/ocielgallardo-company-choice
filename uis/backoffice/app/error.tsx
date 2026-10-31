"use client";

import Link from "next/link";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/** Route-level error boundary: keeps the shell and offers a retry instead of a blank page. */
export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <section
      role="alert"
      className="mx-auto max-w-lg space-y-4 rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Something went wrong</h1>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        This section could not be displayed. You can try again or go back to the dashboard.
      </p>
      {error.digest ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">Reference: {error.digest}</p>
      ) : null}
      <div className="flex justify-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Go to dashboard
        </Link>
      </div>
    </section>
  );
}
