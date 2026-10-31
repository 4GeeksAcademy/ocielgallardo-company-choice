"use client";

import { useState } from "react";
import type { Application, RecordCreateInput } from "@/types/application";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface ApplicationFormProps {
  mode: "create" | "edit";
  initialData?: Application | null;
  isSubmitting: boolean;
  onSubmit: (data: RecordCreateInput) => Promise<void>;
  onCancel: () => void;
}

interface FormState {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string;
  experience_years: string;
}

interface FormErrors {
  full_name?: string;
  email?: string;
  phone?: string;
  position?: string;
  experience_years?: string;
}

const emptyState: FormState = {
  full_name: "",
  email: "",
  phone: "",
  position: "",
  linkedin_url: "",
  experience_years: "",
};

function toFormState(initialData?: Application | null): FormState {
  if (!initialData) return emptyState;

  return {
    full_name: initialData.full_name,
    email: initialData.email,
    phone: initialData.phone,
    position: initialData.position,
    linkedin_url: initialData.linkedin_url ?? "",
    experience_years: String(initialData.experience_years),
  };
}

function validateForm(values: FormState): FormErrors {
  const errors: FormErrors = {};

  if (!values.full_name.trim()) errors.full_name = "Name is required.";
  if (!values.email.trim()) {
    errors.email = "Email is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
    errors.email = "Enter a valid email.";
  }
  if (!values.phone.trim()) errors.phone = "Phone is required.";
  if (!values.position.trim()) errors.position = "Position is required.";
  if (!values.experience_years.trim()) {
    errors.experience_years = "Experience is required.";
  } else if (Number.isNaN(Number(values.experience_years)) || Number(values.experience_years) < 0) {
    errors.experience_years = "Enter a valid number of years of experience.";
  }

  return errors;
}

export function ApplicationForm({
  mode,
  initialData,
  isSubmitting,
  onSubmit,
  onCancel,
}: ApplicationFormProps) {
  const [values, setValues] = useState<FormState>(() => toFormState(initialData));
  const [errors, setErrors] = useState<FormErrors>({});
  const [formStatus, setFormStatus] = useState<string | null>(null);

  const handleChange = (field: keyof FormState, value: string) => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const nextErrors = validateForm(values);
    setErrors(nextErrors);
    setFormStatus(null);

    if (Object.keys(nextErrors).length > 0) return;

    const payload: RecordCreateInput = {
      full_name: values.full_name.trim(),
      email: values.email.trim(),
      phone: values.phone.trim(),
      position: values.position.trim(),
      linkedin_url: values.linkedin_url.trim() || null,
      experience_years: Number(values.experience_years),
    };

    try {
      await onSubmit(payload);
      setFormStatus(
        mode === "create"
          ? "Application added."
          : "Application updated."
      );
    } catch {
      setFormStatus("Could not save the application. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Full name"
          name="full_name"
          value={values.full_name}
          onChange={(event) => handleChange("full_name", event.target.value)}
          error={errors.full_name}
        />
        <Input
          label="Email"
          name="email"
          type="email"
          value={values.email}
          onChange={(event) => handleChange("email", event.target.value)}
          error={errors.email}
        />
        <Input
          label="Phone"
          name="phone"
          value={values.phone}
          onChange={(event) => handleChange("phone", event.target.value)}
          error={errors.phone}
        />
        <Input
          label="Position"
          name="position"
          value={values.position}
          onChange={(event) => handleChange("position", event.target.value)}
          error={errors.position}
        />
        <Input
          label="Years of experience"
          name="experience_years"
          type="number"
          min="0"
          step="0.5"
          value={values.experience_years}
          onChange={(event) => handleChange("experience_years", event.target.value)}
          error={errors.experience_years}
        />
        <Input
          label="LinkedIn (optional)"
          name="linkedin_url"
          value={values.linkedin_url}
          onChange={(event) => handleChange("linkedin_url", event.target.value)}
        />
      </div>

      {formStatus && (
        <p
          className={`text-sm ${formStatus.includes("Could not") ? "text-red-600 dark:text-red-400" : "text-emerald-700 dark:text-emerald-400"}`}
          aria-live="polite"
        >
          {formStatus}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting
            ? "Saving…"
            : mode === "create"
              ? "Add application"
              : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
