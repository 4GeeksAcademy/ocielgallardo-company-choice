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
      setFormError("El enlace de restablecimiento no es válido o ha expirado.");
      return;
    }

    if (!newPassword || newPassword.length < 8) {
      setFieldError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    if (!confirmPassword || newPassword !== confirmPassword) {
      setFieldError("Las contraseñas no coinciden.");
      return;
    }

    await runSubmit(async () => {
      try {
        await resetPassword({ token: effectiveToken, newPassword });
        router.replace("/login?reset=success");
      } catch (err) {
        if (err instanceof HealthcoreApiError) {
          setFormError(err.message || "Token inválido o expirado.");
        } else {
          setFormError("Token inválido o expirado.");
        }
      }
    });
  }

  if (!effectiveToken) {
    return (
      <div className="space-y-4">
        <FormMessage variant="error">
          El enlace de restablecimiento no es válido o ha expirado.
        </FormMessage>
        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          <Link href="/forgot-password" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
            Solicitar un nuevo enlace
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Input
        label="Nueva contraseña"
        name="newPassword"
        type="password"
        autoComplete="new-password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
        error={fieldError ?? undefined}
      />
      <Input
        label="Confirmar nueva contraseña"
        name="confirmPassword"
        type="password"
        autoComplete="new-password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        required
      />

      {formError ? <FormMessage variant="error">{formError}</FormMessage> : null}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Actualizando…" : "Actualizar contraseña"}
      </Button>

      {formError && (
        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          <Link href="/forgot-password" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
            ¿Solicitar un nuevo enlace?
          </Link>
        </p>
      )}
    </form>
  );
}

