"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { forgotPassword } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes("@")) {
      setError("Introduce un email válido.");
      return;
    }

    setIsSubmitting(true);
    try {
      await forgotPassword(trimmed);
      setSent(true);
    } catch (err) {
      if (err instanceof HealthcoreApiError) {
        setError(err.message || "No se pudo enviar el enlace. Inténtalo de nuevo.");
      } else {
        setError("No se pudo enviar el enlace. Inténtalo de nuevo.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (sent) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-slate-700 dark:text-slate-200" role="status">
          Si esa dirección está registrada, recibirás un enlace en breve para restablecer tu contraseña.
        </p>
        <p className="text-center text-sm text-slate-600 dark:text-slate-300">
          <Link href="/login" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
            Volver a iniciar sesión
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Input
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        error={error ?? undefined}
      />

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Enviando…" : "Enviar enlace"}
      </Button>
    </form>
  );
}

