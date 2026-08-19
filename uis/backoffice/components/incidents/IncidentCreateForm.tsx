"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  getFieldErrors,
  HealthcoreApiError,
} from "@/lib/services/healthcoreClient";
import {
  createIncident,
  friendlyIncidentError,
} from "@/lib/services/incidentsManagerApi";
import type {
  IncidentBranch,
  IncidentCategory,
  IncidentCreateInput,
  IncidentOrigin,
  IncidentStatus,
} from "@/types/incidentManager";
import {
  INCIDENT_BRANCH_OPTIONS,
  INCIDENT_CATEGORY_OPTIONS,
  INCIDENT_ORIGIN_OPTIONS,
  INCIDENT_STATUS_OPTIONS,
} from "@/types/incidentManager";

interface FormState {
  title: string;
  description: string;
  category: IncidentCategory | "";
  origin: IncidentOrigin | "";
  branch: IncidentBranch | "";
  status: IncidentStatus;
}

interface FormErrors {
  title?: string;
  description?: string;
  category?: string;
  origin?: string;
  branch?: string;
  status?: string;
}

const initialState: FormState = {
  title: "",
  description: "",
  category: "",
  origin: "",
  branch: "",
  status: "open",
};

function validate(values: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!values.title.trim()) {
    errors.title = "Title is required.";
  }
  if (!values.description.trim()) {
    errors.description = "Description is required.";
  }
  if (!values.category) {
    errors.category = "Select a category.";
  }
  if (!values.origin) {
    errors.origin = "Select an origin.";
  }
  if (!values.branch) {
    errors.branch = "Select a branch (use Central when not clinic-specific).";
  }
  return errors;
}

export function IncidentCreateForm() {
  const [values, setValues] = useState<FormState>(initialState);
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const branchHighlighted = values.origin === "branch";

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const nextErrors = validate(values);
    setErrors(nextErrors);
    setFormError(null);
    setSuccessMessage(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const payload: IncidentCreateInput = {
      title: values.title.trim(),
      description: values.description.trim(),
      category: values.category as IncidentCategory,
      origin: values.origin as IncidentOrigin,
      branch: values.branch as IncidentBranch,
      status: values.status,
    };

    setIsSubmitting(true);
    try {
      const created = await createIncident(payload);
      setValues(initialState);
      setErrors({});
      setSuccessMessage(
        `Incident #${created.id} registered successfully. The form has been cleared.`
      );
    } catch (err) {
      if (err instanceof HealthcoreApiError) {
        const fieldErrors = getFieldErrors(err.details);
        if (fieldErrors) {
          setErrors(fieldErrors as FormErrors);
        }
      }
      setFormError(
        friendlyIncidentError(
          err,
          "Could not register the incident. Please review the form and try again."
        )
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div
        className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"
        role="note"
      >
        <p className="font-semibold">Patient data warning (required)</p>
        <p className="mt-1">
          Do not enter identifying patient data (name, date of birth, medical
          record number, contact details). Reference patients only with an opaque
          internal identifier if needed.
        </p>
      </div>

      <Input
        label="Title"
        name="title"
        value={values.title}
        onChange={(event) =>
          setValues((current) => ({ ...current, title: event.target.value }))
        }
        error={errors.title}
        disabled={isSubmitting}
        required
      />

      <div className="space-y-1.5">
        <label
          htmlFor="description"
          className="block text-sm font-medium text-slate-700"
        >
          Description
        </label>
        <textarea
          id="description"
          name="description"
          rows={5}
          value={values.description}
          disabled={isSubmitting}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={
            errors.description ? "description-error" : "description-hint"
          }
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              description: event.target.value,
            }))
          }
          className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 ${
            errors.description ? "border-red-500" : "border-slate-200"
          }`}
          required
        />
        <p id="description-hint" className="text-xs text-slate-500">
          Free text — highest risk for accidental patient identifiers. Keep it
          operational and anonymous.
        </p>
        {errors.description ? (
          <p id="description-error" className="text-sm text-red-600" role="alert">
            {errors.description}
          </p>
        ) : null}
      </div>

      <Select
        label="Category"
        name="category"
        value={values.category}
        disabled={isSubmitting}
        onChange={(event) =>
          setValues((current) => ({
            ...current,
            category: event.target.value as IncidentCategory | "",
          }))
        }
        options={[
          { value: "", label: "Select category" },
          ...INCIDENT_CATEGORY_OPTIONS,
        ]}
      />
      {errors.category ? (
        <p className="-mt-3 text-sm text-red-600" role="alert">
          {errors.category}
        </p>
      ) : null}

      <Select
        label="Origin"
        name="origin"
        value={values.origin}
        disabled={isSubmitting}
        onChange={(event) =>
          setValues((current) => ({
            ...current,
            origin: event.target.value as IncidentOrigin | "",
          }))
        }
        options={[
          { value: "", label: "Select origin" },
          ...INCIDENT_ORIGIN_OPTIONS,
        ]}
      />
      {errors.origin ? (
        <p className="-mt-3 text-sm text-red-600" role="alert">
          {errors.origin}
        </p>
      ) : null}

      <div
        className={
          branchHighlighted
            ? "rounded-lg border-2 border-blue-500 bg-blue-50 p-3"
            : undefined
        }
      >
        <Select
          label="Branch"
          name="branch"
          value={values.branch}
          disabled={isSubmitting}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              branch: event.target.value as IncidentBranch | "",
            }))
          }
          options={[
            { value: "", label: "Select branch" },
            ...INCIDENT_BRANCH_OPTIONS,
          ]}
        />
        {branchHighlighted ? (
          <p className="mt-2 text-xs font-medium text-blue-800">
            Origin is Branch — confirm you are reporting from the correct clinic.
          </p>
        ) : (
          <p className="mt-2 text-xs text-slate-500">
            Always required. Use Central when the incident is not tied to a
            specific clinic.
          </p>
        )}
        {errors.branch ? (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors.branch}
          </p>
        ) : null}
      </div>

      <Select
        label="Initial status"
        name="status"
        value={values.status}
        disabled={isSubmitting}
        onChange={(event) =>
          setValues((current) => ({
            ...current,
            status: event.target.value as IncidentStatus,
          }))
        }
        options={INCIDENT_STATUS_OPTIONS}
      />
      {errors.status ? (
        <p className="-mt-3 text-sm text-red-600" role="alert">
          {errors.status}
        </p>
      ) : null}

      {formError ? (
        <p className="text-sm text-red-600" role="alert">
          {formError}
        </p>
      ) : null}
      {successMessage ? (
        <p className="text-sm text-emerald-700" role="status">
          {successMessage}
        </p>
      ) : null}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Submitting…" : "Register incident"}
      </Button>
    </form>
  );
}
