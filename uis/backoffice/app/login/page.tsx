import { LoginForm } from "@/components/forms/LoginForm";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const reset = params.reset;
  const resetSuccess = reset === "success";

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-800 px-4 py-10">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shadow-sm sm:p-8">
        <div className="space-y-1 text-center">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
            HealthCore
          </p>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Iniciar sesión</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Accede al backoffice interno con tu cuenta.
          </p>
        </div>
        {resetSuccess && (
          <div
            className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/40 p-3 text-sm text-green-800 dark:text-green-300"
            role="status"
          >
            Contraseña actualizada. Ya puedes iniciar sesión.
          </div>
        )}
        <LoginForm />
      </div>
    </div>
  );
}
