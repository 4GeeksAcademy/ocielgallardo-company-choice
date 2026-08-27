import { Suspense } from "react";
import { ResetPasswordTokenReader } from "@/components/forms/ResetPasswordTokenReader";

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-800 px-4 py-10">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shadow-sm sm:p-8">
        <div className="space-y-1 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
            HealthCore
          </p>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Nueva contraseña</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Crea una nueva contraseña para tu cuenta.
          </p>
        </div>
        <Suspense
          fallback={
            <p className="text-center text-sm text-slate-500 dark:text-slate-400">Cargando…</p>
          }
        >
          <ResetPasswordTokenReader />
        </Suspense>
      </div>
    </div>
  );
}
