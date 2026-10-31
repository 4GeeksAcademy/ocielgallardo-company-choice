"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { FormMessage } from "@/components/ui/FormMessage";
import { Input } from "@/components/ui/Input";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { resetPassword } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";

export function ResetPasswordForm({ token }: { token?: string | null }) {
  const router = useRouter();
  const effectiveToken = useMemo(() => token ?? null, [token]);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const { error: formError, setError: setFormError, isSubmitting, runSubmit } = useFormSubmit();

  useEffect(() => {
    setFormError(null);
    setFieldError(null);
  }, [effectiveToken, setFormError]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldError(null);
    setFormError(null);

    if (!effectiveToken) {
      setFormError("This reset link is invalid or has expired.");
      return;
    }

    if (!newPassword || newPassword.length < 8) {
      setFieldError("Password must be at least 8 characters.");
      return;
    }

    if (!confirmPassword || newPassword !== confirmPassword) {
      setFieldError("Passwords do not match.");
      return;
    }

    await runSubmit(async () => {
      try {
        await resetPassword({ token: effectiveToken, newPassword });
        router.replace("/login?reset=success");
      } catch (err) {
        if (err instanceof HealthcoreApiError) {
          setFormError(err.message || "Invalid or expired token.");
        } else {
          setFormError("Invalid or expired token.");
        }
      }
    });
  }

  if (!effectiveToken) {
    return (
      <div className="space-y-4">
        <FormMessage variant="error">
          This reset link is invalid or has expired.
        </FormMessage>
        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          <Link href="/forgot-password" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
            Request a new link
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Input
        label="New password"
        name="newPassword"
        type="password"
        autoComplete="new-password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
        error={fieldError ?? undefined}
      />
      <Input
        label="Confirm new password"
        name="confirmPassword"
        type="password"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
      />

      {formError ? <FormMessage variant="error">{formError}</FormMessage> : null}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Updating…" : "Update password"}
      </Button>

      {formError && (
        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          <Link href="/forgot-password" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
            Request a new link?
          </Link>
        </p>
      )}
    </form>
  );
}

