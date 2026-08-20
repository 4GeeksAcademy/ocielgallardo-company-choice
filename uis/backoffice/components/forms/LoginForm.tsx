"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { login } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Introduce email y contraseña.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      router.replace("/");
    } catch (err) {
      if (err instanceof HealthcoreApiError) {
        setError(
          err.status === 401
            ? "Credenciales incorrectas."
            : err.message
        );
      } else {
        setError("No se pudo iniciar sesión. Inténtalo de nuevo.");
      }
    } finally {
      setIsSubmitting(false);
    }
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
      <Input
        label="Contraseña"
        name="password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Entrando…" : "Iniciar sesión"}
      </Button>

      <p className="text-center text-sm text-slate-600">
        ¿No tienes cuenta?{" "}
        <Link href="/register" className="font-medium text-blue-600 hover:text-blue-700">
          Regístrate
        </Link>
      </p>
      <p className="text-center text-sm text-slate-600">
        <Link href="/forgot-password" className="font-medium text-blue-600 hover:text-blue-700">
          ¿Olvidaste tu contraseña?
        </Link>
      </p>
    </form>
  );
}
