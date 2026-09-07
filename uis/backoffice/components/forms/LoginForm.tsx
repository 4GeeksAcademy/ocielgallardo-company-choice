"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { FormMessage } from "@/components/ui/FormMessage";
import { Input } from "@/components/ui/Input";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { login } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";
import { track } from "@/lib/services/telemetry";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { error, setError, isSubmitting, runSubmit } = useFormSubmit();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!email.trim() || !password) {
      setError("Introduce email y contraseña.");
      return;
    }

    await runSubmit(async () => {
      try {
        await login({ email: email.trim(), password });
        router.replace("/");
      } catch (err) {
        const status = err instanceof HealthcoreApiError ? err.status : 0;
        track("login_failed", {
          http_status: status,
        });
        if (err instanceof HealthcoreApiError) {
          setError(
            err.status === 401
              ? "Credenciales incorrectas."
              : err.message
          );
        } else {
          setError("No se pudo iniciar sesión. Inténtalo de nuevo.");
        }
      }
    });
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

      {error ? <FormMessage variant="error">{error}</FormMessage> : null}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? "Entrando…" : "Iniciar sesión"}
      </Button>

      <p className="text-center text-sm text-slate-600 dark:text-slate-300">
        ¿No tienes cuenta?{" "}
        <Link href="/register" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
          Regístrate
        </Link>
      </p>
      <p className="text-center text-sm text-slate-600 dark:text-slate-300">
        <Link href="/forgot-password" className="font-medium text-blue-600 dark:text-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
          ¿Olvidaste tu contraseña?
        </Link>
      </p>
    </form>
  );
}
