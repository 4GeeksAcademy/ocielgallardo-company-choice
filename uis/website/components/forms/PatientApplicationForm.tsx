"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { FormStatusMessage } from "@/components/ui/FormStatusMessage";

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

const REDIRECT_DELAY_MS = 2000;

export function PatientApplicationForm() {
  const router = useRouter();
  const successRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<FormData>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [status, setStatus] = useState<"idle" | "success">("idle");
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const hasErrors = useMemo(() => Object.keys(errors).length > 0, [errors]);
  const isSuccess = status === "success";

  useEffect(() => {
    if (!isSuccess) return;

    successRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    successRef.current?.focus({ preventScroll: true });

    const timerId = window.setTimeout(() => {
      router.replace("/");
      window.setTimeout(() => {
        if (window.location.pathname !== "/") {
          window.location.assign("/");
        }
      }, 300);
    }, REDIRECT_DELAY_MS);

    return () => window.clearTimeout(timerId);
  }, [isSuccess, router]);

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
    if (isSuccess) return;
    const updated = { ...data, [key]: value };
    setData(updated);
    setErrors(validate(updated));
  };

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSuccess) return;

    setSubmitAttempted(true);
    const nextErrors = validate(data);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setStatus("success");
  };

  if (isSuccess) {
    return (
      <div
        ref={successRef}
        tabIndex={-1}
        role="region"
        aria-label="Application submitted"
        className="outline-none"
      >
        <FormStatusMessage variant="success" className="p-6">
          <p className="text-lg font-semibold">Application submitted successfully.</p>
          <p className="mt-2 text-sm">
            Thank you for your request. Redirecting to the home page…
          </p>
        </FormStatusMessage>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {submitAttempted && hasErrors ? (
        <FormStatusMessage variant="error">
          Please complete all required fields and accept the consent checkbox before submitting.
        </FormStatusMessage>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <fieldset className="space-y-4">
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

            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="country">
              Country
              <select
                id="country"
                value={data.country}
                onChange={(event) => update("country", event.target.value as FormData["country"])}
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
              >
                <option value="">Select country</option>
                <option value="US">US</option>
                <option value="United Kingdom">United Kingdom</option>
              </select>
              {errors.country ? <span className="mt-1 block text-xs text-red-600">{errors.country}</span> : null}
            </label>
          </div>

          <InputField
            label="Preferred clinic"
            value={data.preferredClinic}
            onChange={(value) => update("preferredClinic", value)}
            error={errors.preferredClinic}
            id="preferredClinic"
          />

          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="reason">
            Reason for appointment
            <textarea
              id="reason"
              value={data.reason}
              onChange={(event) => update("reason", event.target.value)}
              rows={4}
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
            />
            {errors.reason ? <span className="mt-1 block text-xs text-red-600">{errors.reason}</span> : null}
          </label>

          <label className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-200" htmlFor="consent">
            <input
              id="consent"
              type="checkbox"
              checked={data.consent}
              onChange={(event) => update("consent", event.target.checked)}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600"
            />
            <span>
              I consent to HealthCore processing this request under HIPAA/UK GDPR obligations.
            </span>
          </label>
          {errors.consent ? <p className="text-xs text-red-600">{errors.consent}</p> : null}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="submit"
              className="rounded-lg bg-(--brand-600) px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-(--brand-700)"
            >
              Submit application
            </button>
            <span className="text-xs text-slate-600 dark:text-slate-400" aria-live="polite">
              {hasErrors ? "Please fix validation errors before submit." : "Form ready."}
            </span>
          </div>
        </fieldset>
      </form>
    </div>
  );
}

interface InputFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  id: string;
  type?: "text" | "email";
}

function InputField({
  label,
  value,
  onChange,
  error,
  id,
  type = "text",
}: InputFieldProps) {
  return (
    <label className="block text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor={id}>
      {label}
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}
