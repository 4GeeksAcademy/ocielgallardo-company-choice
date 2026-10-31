"use client";

import Link from "next/link";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto flex min-h-[60vh] w-full max-w-xl flex-col items-center justify-center gap-4 px-4 py-12 text-center focus:outline-none"
    >
      <div role="alert" className="space-y-3">
        <h1 className="font-serif text-2xl font-bold text-slate-900 dark:text-slate-50">Something went wrong</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          We could not load this page. Please try again in a moment.
        </p>
        {error.digest ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">Reference: {error.digest}</p>
        ) : null}
      </div>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-lg bg-primary-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Back to home
        </Link>
      </div>
    </main>
  );
}
