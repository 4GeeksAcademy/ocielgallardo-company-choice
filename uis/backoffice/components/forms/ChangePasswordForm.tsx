"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { FormMessage } from "@/components/ui/FormMessage";
import { Input } from "@/components/ui/Input";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { changePassword } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";

export function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const {
    error: formError,
    setError: setFormError,
    success: formSuccess,
    setSuccess: setFormSuccess,
    isSubmitting,
    runSubmit,
  } = useFormSubmit();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!newPassword || newPassword.length < 8) {
      setFormError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }

    if (newPassword !== confirmNewPassword) {
      setFormError("Las nuevas contraseñas no coinciden.");
      return;
    }

    await runSubmit(async () => {
      try {
        await changePassword({ currentPassword, newPassword });
        setFormSuccess("Contraseña actualizada correctamente.");
        setCurrentPassword("");
        setNewPassword("");
        setConfirmNewPassword("");
      } catch (err) {
        if (err instanceof HealthcoreApiError) {
          setFormError(err.message || "No se pudo cambiar la contraseña.");
        } else {
          setFormError("No se pudo cambiar la contraseña. Inténtalo de nuevo.");
        }
      }
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Input
        label="Contraseña actual"
        name="currentPassword"
        type="password"
        autoComplete="current-password"
        value={currentPassword}
        onChange={(e) => setCurrentPassword(e.target.value)}
        required
      />
      <Input
        label="Nueva contraseña"
        name="newPassword"
        type="password"
        autoComplete="new-password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
      />
      <Input
        label="Confirmar nueva contraseña"
        name="confirmNewPassword"
        type="password"
        autoComplete="new-password"
        value={confirmNewPassword}
        onChange={(e) => setConfirmNewPassword(e.target.value)}
        required
        error={formError ?? undefined}
      />

      {formError ? <FormMessage variant="error">{formError}</FormMessage> : null}

      {formSuccess ? <FormMessage variant="success">{formSuccess}</FormMessage> : null}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Actualizando…" : "Actualizar contraseña"}
      </Button>
    </form>
  );
}

