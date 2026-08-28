import { Suspense } from "react";
import { ResetPasswordTokenReader } from "@/components/forms/ResetPasswordTokenReader";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default function ResetPasswordPage() {
  return (
    <AuthPageShell
      title="Nueva contraseña"
      description="Crea una nueva contraseña para tu cuenta."
    >
      <Suspense
        fallback={
          <p className="text-center text-sm text-slate-500 dark:text-slate-400">Cargando…</p>
        }
      >
        <ResetPasswordTokenReader />
      </Suspense>
    </AuthPageShell>
  );
}
