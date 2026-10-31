import { Suspense } from "react";
import { ResetPasswordTokenReader } from "@/components/forms/ResetPasswordTokenReader";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default function ResetPasswordPage() {
  return (
    <AuthPageShell
      title="New password"
      description="Create a new password for your account."
    >
      <Suspense
        fallback={
          <p className="text-center text-sm text-slate-500 dark:text-slate-400">Loading…</p>
        }
      >
        <ResetPasswordTokenReader />
      </Suspense>
    </AuthPageShell>
  );
}
