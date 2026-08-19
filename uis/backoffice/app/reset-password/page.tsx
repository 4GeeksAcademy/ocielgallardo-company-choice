import { Suspense } from "react";
import { ResetPasswordTokenReader } from "@/components/forms/ResetPasswordTokenReader";

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="space-y-1 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            HealthCore
          </p>
          <h1 className="text-xl font-semibold text-slate-900">Nueva contraseña</h1>
          <p className="text-sm text-slate-600">
            Crea una nueva contraseña para tu cuenta.
          </p>
        </div>
        <Suspense
          fallback={
            <p className="text-center text-sm text-slate-500">Cargando…</p>
          }
        >
          <ResetPasswordTokenReader />
        </Suspense>
      </div>
    </div>
  );
}
