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
      setFormError("The new password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmNewPassword) {
      setFormError("The new passwords do not match.");
      return;
    }

    await runSubmit(async () => {
      try {
        await changePassword({ currentPassword, newPassword });
        setFormSuccess("Password updated.");
        setCurrentPassword("");
        setNewPassword("");
        setConfirmNewPassword("");
      } catch (err) {
        if (err instanceof HealthcoreApiError) {
          setFormError(err.message || "Could not change the password.");
        } else {
          setFormError("Could not change the password. Please try again.");
        }
      }
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Input
        label="Current password"
        name="currentPassword"
        type="password"
        autoComplete="current-password"
        value={currentPassword}
        onChange={(e) => setCurrentPassword(e.target.value)}
        required
      />
      <Input
        label="New password"
        name="newPassword"
        type="password"
        autoComplete="new-password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        required
      />
      <Input
        label="Confirm new password"
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
        {isSubmitting ? "Updating…" : "Update password"}
      </Button>
    </form>
  );
}

