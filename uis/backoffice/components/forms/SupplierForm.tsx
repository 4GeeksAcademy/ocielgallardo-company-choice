"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type {
  ComplianceAgreement,
  SupplierCategory,
  SupplierCreateInput,
  SupplierStatus,
} from "@/types/suppliers";
import {
  currencyForCountry,
  SUPPLIER_CATEGORY_OPTIONS,
  SUPPLIER_STATUS_OPTIONS,
} from "@/types/suppliers";

interface SupplierFormProps {
  isSubmitting: boolean;
  onSubmit: (data: SupplierCreateInput) => Promise<void>;
  onCancel: () => void;
}

interface FormState {
  name: string;
  country: "USA" | "UK";
  categories: SupplierCategory[];
  monthly_rate: string;
  status: SupplierStatus;
  compliance_agreement: ComplianceAgreement | "";
  contract_renewal_date: string;
  contact_email: string;
  notes: string;
}

interface FormErrors {
  name?: string;
  categories?: string;
  monthly_rate?: string;
  contact_email?: string;
}

const initialState: FormState = {
  name: "",
  country: "USA",
  categories: [],
  monthly_rate: "",
  status: "active",
  compliance_agreement: "",
  contract_renewal_date: "",
  contact_email: "",
  notes: "",
};

function validate(values: FormState): FormErrors {
  const errors: FormErrors = {};

  if (!values.name.trim()) {
    errors.name = "El nombre es obligatorio.";
  }
  if (values.categories.length === 0) {
    errors.categories = "Selecciona al menos una categoria.";
  }
  if (!values.monthly_rate.trim()) {
    errors.monthly_rate = "La tarifa mensual es obligatoria.";
  } else if (Number.isNaN(Number(values.monthly_rate)) || Number(values.monthly_rate) <= 0) {
    errors.monthly_rate = "Introduce una tarifa mayor que 0.";
  }
  if (
    values.contact_email.trim() &&
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.contact_email)
  ) {
    errors.contact_email = "Introduce un email valido.";
  }

  return errors;
}

export function SupplierForm({ isSubmitting, onSubmit, onCancel }: SupplierFormProps) {
  const [values, setValues] = useState<FormState>(initialState);
  const [errors, setErrors] = useState<FormErrors>({});
  const [formStatus, setFormStatus] = useState<string | null>(null);

  function toggleCategory(category: SupplierCategory) {
    setValues((current) => ({
      ...current,
      categories: current.categories.includes(category)
        ? current.categories.filter((value) => value !== category)
        : [...current.categories, category],
    }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const nextErrors = validate(values);
    setErrors(nextErrors);
    setFormStatus(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    try {
      await onSubmit({
        name: values.name.trim(),
        country: values.country,
        categories: values.categories,
        monthly_rate: Number(values.monthly_rate),
        currency: currencyForCountry(values.country),
        status: values.status,
        compliance_agreement: values.compliance_agreement || null,
        contract_renewal_date: values.contract_renewal_date || null,
        contact_email: values.contact_email.trim() || null,
        notes: values.notes.trim() || null,
      });
      setFormStatus("Proveedor registrado correctamente.");
      setValues(initialState);
    } catch (err) {
      setFormStatus(
        err instanceof Error ? err.message : "No se pudo registrar el proveedor."
      );
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Supplier name"
          name="name"
          value={values.name}
          onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))}
          error={errors.name}
        />

        <Select
          label="Country"
          name="country"
          value={values.country}
          options={[
            { value: "USA", label: "USA" },
            { value: "UK", label: "UK" },
          ]}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              country: event.target.value as "USA" | "UK",
            }))
          }
        />

        <Input
          label="Monthly rate"
          name="monthly_rate"
          type="number"
          min="0.01"
          step="0.01"
          value={values.monthly_rate}
          onChange={(event) =>
            setValues((current) => ({ ...current, monthly_rate: event.target.value }))
          }
          error={errors.monthly_rate}
        />

        <Input
          label="Currency"
          name="currency"
          value={currencyForCountry(values.country)}
          readOnly
        />

        <Select
          label="Status"
          name="status"
          value={values.status}
          options={SUPPLIER_STATUS_OPTIONS.map((option) => ({
            value: option.value,
            label: option.label,
          }))}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              status: event.target.value as SupplierStatus,
            }))
          }
        />

        <Select
          label="Compliance agreement"
          name="compliance_agreement"
          value={values.compliance_agreement}
          options={[
            { value: "", label: "Not set" },
            { value: "BAA", label: "BAA" },
            { value: "DPA", label: "DPA" },
            { value: "both", label: "Both" },
          ]}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              compliance_agreement: event.target.value as ComplianceAgreement | "",
            }))
          }
        />

        <Input
          label="Contract renewal date"
          name="contract_renewal_date"
          type="date"
          value={values.contract_renewal_date}
          onChange={(event) =>
            setValues((current) => ({
              ...current,
              contract_renewal_date: event.target.value,
            }))
          }
        />

        <Input
          label="Contact email"
          name="contact_email"
          type="email"
          value={values.contact_email}
          onChange={(event) =>
            setValues((current) => ({ ...current, contact_email: event.target.value }))
          }
          error={errors.contact_email}
        />

        <Input
          label="Notes"
          name="notes"
          value={values.notes}
          onChange={(event) => setValues((current) => ({ ...current, notes: event.target.value }))}
        />
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium text-slate-700">Categories</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {SUPPLIER_CATEGORY_OPTIONS.map((option) => (
            <label
              key={option.value}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
            >
              <input
                type="checkbox"
                checked={values.categories.includes(option.value)}
                onChange={() => toggleCategory(option.value)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
        {errors.categories && (
          <p className="text-sm text-red-600" role="alert">
            {errors.categories}
          </p>
        )}
      </div>

      {formStatus && (
        <p
          className={`text-sm ${formStatus.includes("No se") || formStatus.includes("Error") ? "text-red-600" : "text-emerald-700"}`}
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
          {isSubmitting ? "Saving..." : "Create supplier"}
        </Button>
      </div>
    </form>
  );
}