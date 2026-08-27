"use client";

import { useEffect, useState } from "react";
import { ProfileForm } from "@/components/forms/ProfileForm";
import { fetchCurrentUser } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";
import type { AuthMeResponse } from "@/types/auth";

export default function ProfilePage() {
  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchCurrentUser();
        if (!cancelled) setMe(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof HealthcoreApiError
              ? err.message
              : "No se pudo cargar el perfil."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Cargando perfil…</p>;
  }

  if (error || !me) {
    return (
      <p className="text-sm text-red-600 dark:text-red-400" role="alert">
        {error ?? "Perfil no disponible."}
      </p>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Mi perfil</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Email de la cuenta y datos de contacto.
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 shadow-sm">
        <ProfileForm me={me} onSaved={setMe} />
      </div>
    </div>
  );
}