"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { updateMyProfile } from "@/lib/services/authApi";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";
import type { AuthMeResponse } from "@/types/auth";

interface ProfileFormProps {
  me: AuthMeResponse;
  onSaved: (me: AuthMeResponse) => void;
}

export function ProfileForm({ me, onSaved }: ProfileFormProps) {
  const [name, setName] = useState(me.profile?.name ?? "");
  const [phone, setPhone] = useState(me.profile?.phone ?? "");
  const [address, setAddress] = useState(me.profile?.address ?? "");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    try {
      const profile = await updateMyProfile({
        name: name.trim() || null,
        phone: phone.trim() || null,
        address: address.trim() || null,
      });
      onSaved({ ...me, profile });
      setSuccess("Perfil actualizado.");
    } catch (err) {
      if (err instanceof HealthcoreApiError) {
        setError(err.message);
      } else {
        setError("No se pudo guardar el perfil. Inténtalo de nuevo.");
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
        value={me.email}
        readOnly
        disabled
      />

      <Input
        label="Nombre"
        name="name"
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <Input
        label="Teléfono"
        name="phone"
        type="tel"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
      />
      <Input
        label="Dirección"
        name="address"
        type="text"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
      {success && (
        <p className="text-sm text-green-700" role="status">
          {success}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Guardando…" : "Guardar cambios"}
      </Button>
    </form>
  );
}