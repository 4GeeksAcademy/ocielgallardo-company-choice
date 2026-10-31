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
      setSuccess("Profile updated.");
    } catch (err) {
      if (err instanceof HealthcoreApiError) {
        setError(err.message);
      } else {
        setError("Could not save your profile. Please try again.");
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
        label="Name"
        name="name"
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <Input
        label="Phone"
        name="phone"
        type="tel"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
      />
      <Input
        label="Address"
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
        {isSubmitting ? "Saving…" : "Save changes"}
      </Button>
    </form>
  );
}