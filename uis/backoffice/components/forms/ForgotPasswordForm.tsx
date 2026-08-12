"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { forgotPassword } from "@/lib/services/authApi";

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
    } catch {
      // Anti-enumeration: never surface provider/API details.
      setError("No se pudo enviar el enlace. Inténtalo de nuevo.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (sent) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-slate-700" role="status">
          Si esa dirección está registrada, recibirás un enlace en breve para restablecer tu contraseña.
        </p>
        <p className="text-center text-sm text-slate-600">
          <Link href="/login" className="font-medium text-blue-600 hover:text-blue-700">
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
        <div className="space-y-1" role="alert">
          <p className="text-sm text-red-600">{error}</p>
          <p className="text-sm text-slate-600">
            <Link href="/login" className="font-medium text-blue-600 hover:text-blue-700">
              Volver al inicio de sesión
            </Link>
          </p>
        </div>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Enviando…" : "Enviar enlace"}
      </Button>
    </form>
  );
}

