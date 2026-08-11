import { ForgotPasswordForm } from "@/components/forms/ForgotPasswordForm";

export default function ForgotPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="space-y-1 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
            HealthCore
          </p>
          <h1 className="text-xl font-semibold text-slate-900">Restablecer contraseña</h1>
          <p className="text-sm text-slate-600">
            Introduce tu email y te enviaremos un enlace para crear una nueva contraseña.
          </p>
        </div>
        <ForgotPasswordForm />
      </div>
    </div>
  );
}

