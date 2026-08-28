import type { ReactNode } from "react";

interface AuthPageShellProps {
  title: string;
  description: string;
  children: ReactNode;
}

/**
 * Shared chrome for public auth pages (login, register, password flows).
 * Provides a single <main> landmark for accessibility.
 */
export function AuthPageShell({ title, description, children }: AuthPageShellProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10 dark:bg-slate-800">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
        <div className="space-y-1 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
            HealthCore
          </p>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">{title}</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">{description}</p>
        </div>
        {children}
      </div>
    </main>
  );
}
