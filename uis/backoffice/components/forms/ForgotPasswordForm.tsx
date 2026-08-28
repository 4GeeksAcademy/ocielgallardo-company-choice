"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { FormMessage } from "@/components/ui/FormMessage";
import { Input } from "@/components/ui/Input";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { forgotPassword } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { error, setError, isSubmitting, runSubmit } = useFormSubmit();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes("@")) {
      setError("Introduce un email válido.");
      return;
    }

    await runSubmit(async () => {
      try {
        await forgotPassword(trimmed);
        setSent(true);
      } catch (err) {
        if (err instanceof HealthcoreApiError) {
          setError(err.message || "No se pudo enviar el enlace. Inténtalo de nuevo.");
        } else {
          setError("No se pudo enviar el enlace. Inténtalo de nuevo.");
        }
      }
    });
  }

  if (sent) {
    return (
      <div className="space-y-4">
        <FormMessage variant="success">
          Si esa dirección está registrada, recibirás un enlace en breve para
          restablecer tu contraseña.
        </FormMessage>
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
      />

      {error ? <FormMessage variant="error">{error}</FormMessage> : null}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Enviando…" : "Enviar enlace"}
      </Button>
    </form>
  );
}

