"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

interface FormData {
  fullName: string;
  email: string;
  phone: string;
  country: "US" | "United Kingdom" | "";
  preferredClinic: string;
  reason: string;
  consent: boolean;
}

interface FormErrors {
  fullName?: string;
  email?: string;
  phone?: string;
  country?: string;
  preferredClinic?: string;
  reason?: string;
  consent?: string;
}

const INITIAL_FORM: FormData = {
  fullName: "",
  email: "",
  phone: "",
  country: "",
  preferredClinic: "",
  reason: "",
  consent: false,
};

type SubmitStatus = "idle" | "loading" | "success" | "error";

/**
 * Demo submit: no backend yet. Structured like a real API call so loading /
 * error / success states and try/catch/finally are exercised.
 */
async function submitPatientApplicationDemo(_payload: FormData): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 400));
  // Demo acknowledgement — replace with real fetch when an intake API exists.
}

export function PatientApplicationForm() {
  const [data, setData] = useState<FormData>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState<SubmitStatus>("idle");

  const hasErrors = useMemo(() => Object.keys(errors).length > 0, [errors]);

  const validate = (input: FormData): FormErrors => {
    const nextErrors: FormErrors = {};

    if (!input.fullName.trim()) nextErrors.fullName = "Full name is required.";
    if (!input.email.trim()) nextErrors.email = "Email is required.";
    else if (!/^\S+@\S+\.\S+$/.test(input.email)) {
      nextErrors.email = "Enter a valid email address.";
    }

    if (!input.phone.trim()) nextErrors.phone = "Phone is required.";
    if (!input.country) nextErrors.country = "Select a country.";
    if (!input.preferredClinic.trim()) nextErrors.preferredClinic = "Preferred clinic is required.";
    if (!input.reason.trim()) nextErrors.reason = "Reason for appointment is required.";
    if (!input.consent) nextErrors.consent = "Consent is required to continue.";

    return nextErrors;
  };

  const update = <K extends keyof FormData>(key: K, value: FormData[K]) => {
    const updated = { ...data, [key]: value };
    setData(updated);
    setErrors(validate(updated));
    if (status === "success" || status === "error") setStatus("idle");
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validate(data);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setStatus("loading");
    try {
      await submitPatientApplicationDemo(data);
      setData(INITIAL_FORM);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <InputField
          label="Full name"
          value={data.fullName}
          onChange={(value) => update("fullName", value)}
          error={errors.fullName}
          id="fullName"
        />
        <InputField
          label="Email"
          value={data.email}
          onChange={(value) => update("email", value)}
          error={errors.email}
          id="email"
          type="email"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <InputField
          label="Phone"
          value={data.phone}
          onChange={(value) => update("phone", value)}
          error={errors.phone}
          id="phone"
        />

        <label className="block text-sm font-medium text-slate-700" htmlFor="country">
          Country
          <select
            id="country"
            value={data.country}
            onChange={(event) => update("country", event.target.value as FormData["country"])}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            aria-invalid={Boolean(errors.country)}
            aria-describedby={errors.country ? "country-error" : undefined}
            disabled={status === "loading"}
          >
            <option value="">Select country</option>
            <option value="US">US</option>
            <option value="United Kingdom">United Kingdom</option>
          </select>
          {errors.country ? (
            <span id="country-error" className="mt-1 block text-xs text-red-700">
              {errors.country}
            </span>
          ) : null}
        </label>
      </div>

      <InputField
        label="Preferred clinic"
        value={data.preferredClinic}
        onChange={(value) => update("preferredClinic", value)}
        error={errors.preferredClinic}
        id="preferredClinic"
        disabled={status === "loading"}
      />

      <label className="block text-sm font-medium text-slate-700" htmlFor="reason">
        Reason for appointment
        <textarea
          id="reason"
          value={data.reason}
          onChange={(event) => update("reason", event.target.value)}
          rows={4}
          className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
          aria-invalid={Boolean(errors.reason)}
          aria-describedby={errors.reason ? "reason-error" : undefined}
          disabled={status === "loading"}
        />
        {errors.reason ? (
          <span id="reason-error" className="mt-1 block text-xs text-red-700">
            {errors.reason}
          </span>
        ) : null}
      </label>

      <label className="flex items-start gap-2 text-sm text-slate-700" htmlFor="consent">
        <input
          id="consent"
          type="checkbox"
          checked={data.consent}
          onChange={(event) => update("consent", event.target.checked)}
          className="mt-1 h-4 w-4 rounded border-slate-300"
          disabled={status === "loading"}
          aria-invalid={Boolean(errors.consent)}
        />
        <span>
          I consent to HealthCore processing this request under HIPAA/UK GDPR obligations.
        </span>
      </label>
      {errors.consent ? <p className="text-xs text-red-700">{errors.consent}</p> : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={status === "loading"}
          className="rounded-md bg-[var(--brand-600)] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--brand-700)] disabled:opacity-60"
        >
          {status === "loading" ? "Submitting…" : "Submit application"}
        </button>
        <span className="text-xs text-slate-500" aria-live="polite">
          {status === "loading"
            ? "Sending your request…"
            : status === "success"
              ? "Application submitted successfully (demo mode)."
              : status === "error"
                ? "We could not submit your application."
                : hasErrors
                  ? "Please fix validation errors before submit."
                  : "Form ready."}
        </span>
      </div>

      {status === "error" ? (
        <div
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
          role="alert"
        >
          <p>Something went wrong while submitting. Your answers were kept.</p>
          <div className="mt-2 flex flex-wrap gap-3">
            <button
              type="submit"
              className="font-medium text-blue-700 underline"
            >
              Try again
            </button>
            <Link href="/" className="font-medium text-blue-700 underline">
              Back to home
            </Link>
          </div>
        </div>
      ) : null}
    </form>
  );
}

interface InputFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  id: string;
  type?: "text" | "email";
  disabled?: boolean;
}

function InputField({
  label,
  value,
  onChange,
  error,
  id,
  type = "text",
  disabled = false,
}: InputFieldProps) {
  const errorId = `${id}-error`;
  return (
    <label className="block text-sm font-medium text-slate-700" htmlFor={id}>
      {label}
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm disabled:opacity-60"
      />
      {error ? (
        <span id={errorId} className="mt-1 block text-xs text-red-700">
          {error}
        </span>
      ) : null}
    </label>
  );
}
