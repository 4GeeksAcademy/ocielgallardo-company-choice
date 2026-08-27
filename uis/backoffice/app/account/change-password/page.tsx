import { ChangePasswordForm } from "@/components/forms/ChangePasswordForm";

export default function ChangePasswordPage() {
  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Cambiar contraseña</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Actualiza tu contraseña ingresando tu contraseña actual.
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 shadow-sm">
        <ChangePasswordForm />
      </div>
    </div>
  );
}

