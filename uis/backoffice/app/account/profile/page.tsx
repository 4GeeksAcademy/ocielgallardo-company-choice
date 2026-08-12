"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ProfileForm } from "@/components/forms/ProfileForm";
import { fetchCurrentUser } from "@/lib/services/authApi";
import type { AuthMeResponse } from "@/types/auth";
import { friendlyApiErrorEs } from "@/lib/utils/friendlyApiError";

export default function ProfilePage() {
  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCurrentUser();
      setMe(data);
    } catch (err) {
      setMe(null);
      setError(
        friendlyApiErrorEs(err, "No se pudo cargar el perfil.")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchCurrentUser();
        if (!cancelled) setMe(data);
      } catch (err) {
        if (!cancelled) {
          setMe(null);
          setError(
            friendlyApiErrorEs(err, "No se pudo cargar el perfil.")
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500">Cargando perfil…</p>;
  }

  if (error || !me) {
    return (
      <div className="space-y-3" role="alert">
        <p className="text-sm text-red-600">
          {error ?? "Perfil no disponible."}
        </p>
        <Button type="button" variant="secondary" onClick={() => void load()}>
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Mi perfil</h1>
        <p className="text-sm text-slate-600">
          Email de la cuenta y datos de contacto.
        </p>
      </div>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <ProfileForm me={me} onSaved={setMe} />
      </div>
    </div>
  );
}
