"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { resetPassword } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";

export function ResetPasswordForm({ token }: { token?: string | null }) {
  const router = useRouter();
  const effectiveToken = useMemo(() => token ?? null, [token]);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setFormError(null);
    setFieldError(null);
  }, [effectiveToken]);

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

    setIsSubmitting(true);
    try {
      await resetPassword({ token: effectiveToken, newPassword });
      router.replace("/login?reset=success");
    } catch (err) {
      if (err instanceof HealthcoreApiError && err.status === 400) {
        setFormError("Token inválido o expirado.");
      } else {
        setFormError(
          "No se pudo restablecer la contraseña. Solicita un nuevo enlace."
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!effectiveToken) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-600" role="alert">
          El enlace de restablecimiento no es válido o ha expirado.
        </p>
        <p className="text-center text-sm text-slate-600">
          <Link href="/forgot-password" className="font-medium text-blue-600 hover:text-blue-700">
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

      {formError && (
        <p className="text-sm text-red-600" role="alert">
          {formError}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Actualizando…" : "Actualizar contraseña"}
      </Button>

      {formError && (
        <p className="text-center text-sm text-slate-600">
          <Link href="/forgot-password" className="font-medium text-blue-600 hover:text-blue-700">
            ¿Solicitar un nuevo enlace?
          </Link>
        </p>
      )}
    </form>
  );
}

