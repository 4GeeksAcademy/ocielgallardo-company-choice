import { LoginForm } from "@/components/forms/LoginForm";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const reset = params.reset;
  const resetSuccess = reset === "success";

  return (
    <AuthPageShell
      title="Sign in"
      description="Access the internal backoffice with your account."
    >
      {resetSuccess && (
        <div
          className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300"
          role="status"
        >
          Password updated. You can now sign in.
        </div>
      )}
      <LoginForm />
    </AuthPageShell>
  );
}
