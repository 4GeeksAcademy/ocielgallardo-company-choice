import { LoginForm } from "@/components/forms/LoginForm";
import { AuthPageShell } from "@/components/layout/AuthPageShell";
import {
  safeNextPath,
  SESSION_EXPIRED_MESSAGE,
  SESSION_EXPIRED_REASON,
} from "@/lib/auth/session";

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const reset = params.reset;
  const resetSuccess = reset === "success";
  const sessionExpired = firstParam(params.reason) === SESSION_EXPIRED_REASON;
  // Validated here and again after login: only in-app paths, never a URL.
  const nextPath = safeNextPath(firstParam(params.next));

  return (
    <AuthPageShell
      title="Sign in"
      description="Access the internal backoffice with your account."
    >
      {sessionExpired && !resetSuccess && (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
          role="status"
        >
          {SESSION_EXPIRED_MESSAGE}
        </div>
      )}
      {resetSuccess && (
        <div
          className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300"
          role="status"
        >
          Password updated. You can now sign in.
        </div>
      )}
      <LoginForm nextPath={nextPath} />
    </AuthPageShell>
  );
}
