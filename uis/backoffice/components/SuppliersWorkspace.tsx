"use client";

import { useMemo, useState } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { SupplierForm } from "@/components/forms/SupplierForm";
import { SupplierStatusBadge } from "@/components/suppliers/SupplierStatusBadge";
import { useSuppliers } from "@/hooks/useSuppliers";
import {
  createSupplier,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/lib/services/suppliersApi";
import {
  SUPPLIER_CATEGORY_LABELS,
  SUPPLIER_CATEGORY_OPTIONS,
  SUPPLIER_COUNTRY_OPTIONS,
  SUPPLIER_STATUS_OPTIONS,
  type Supplier,
  type SupplierCategory,
  type SupplierStatus,
} from "@/types/suppliers";

function formatMoney(value: number, currency: Supplier["currency"]) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(value);
}

function formatDate(value: string | null) {
  if (!value) return "Not set";
  return new Date(value).toLocaleString();
}

export function SuppliersWorkspace() {
  const { suppliers, setSuppliers, isLoading, isError, error, reload } = useSuppliers();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [countryFilter, setCountryFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [updatingRateId, setUpdatingRateId] = useState<number | null>(null);
  const [updatingStatusId, setUpdatingStatusId] = useState<number | null>(null);
  const [rateDrafts, setRateDrafts] = useState<Record<number, string>>({});
  const [statusDrafts, setStatusDrafts] = useState<Record<number, SupplierStatus>>({});

  const filteredSuppliers = useMemo(() => {
    return suppliers.filter((supplier) => {
      if (countryFilter && supplier.country !== countryFilter) return false;
      if (categoryFilter && !supplier.categories.includes(categoryFilter as SupplierCategory)) {
        return false;
      }
      return true;
    });
  }, [suppliers, countryFilter, categoryFilter]);

  async function handleCreateSupplier(input: Parameters<typeof createSupplier>[0]) {
    setIsSubmittingForm(true);
    setActionError(null);
    setActionFeedback(null);
    try {
      const created = await createSupplier(input);
      setSuppliers((current) => [created, ...current]);
      setShowCreateForm(false);
      setActionFeedback("Supplier created successfully.");
    } finally {
      setIsSubmittingForm(false);
    }
  }

  async function handleRateUpdate(supplier: Supplier) {
    const draft = rateDrafts[supplier.id] ?? String(supplier.monthly_rate);
    setActionError(null);
    setActionFeedback(null);
    setUpdatingRateId(supplier.id);

    try {
      const updated = await updateSupplierRate(supplier.id, {
        monthly_rate: Number(draft),
      });
      setSuppliers((current) =>
        current.map((item) => (item.id === supplier.id ? updated : item))
      );
      setRateDrafts((current) => ({ ...current, [supplier.id]: String(updated.monthly_rate) }));
      setActionFeedback(`Rate updated for ${supplier.name}.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not update rate.");
    } finally {
      setUpdatingRateId(null);
    }
  }

  async function handleStatusUpdate(supplier: Supplier) {
    const draft = statusDrafts[supplier.id] ?? supplier.status;
    setActionError(null);
    setActionFeedback(null);
    setUpdatingStatusId(supplier.id);

    try {
      const updated = await updateSupplierStatus(supplier.id, { status: draft });
      setSuppliers((current) =>
        current.map((item) => (item.id === supplier.id ? updated : item))
      );
      setStatusDrafts((current) => ({ ...current, [supplier.id]: updated.status }));
      setActionFeedback(`Status updated for ${supplier.name}.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not update status.");
    } finally {
      setUpdatingStatusId(null);
    }
  }

  return (
    <div className="space-y-4">
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Supplier Directory</h2>
            <p className="text-sm text-slate-600">
              Centralized vendor directory for procurement and compliance teams.
            </p>
          </div>
          <Button onClick={() => setShowCreateForm((current) => !current)}>
            {showCreateForm ? "Close form" : "New supplier"}
          </Button>
        </div>

        {showCreateForm && (
          <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
            <h3 className="mb-4 text-base font-semibold text-slate-900">Register supplier</h3>
            <SupplierForm
              isSubmitting={isSubmittingForm}
              onSubmit={handleCreateSupplier}
              onCancel={() => setShowCreateForm(false)}
            />
          </section>
        )}

        <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Filter by country"
              value={countryFilter}
              options={SUPPLIER_COUNTRY_OPTIONS.map((option) => ({
                value: option.value,
                label: option.label,
              }))}
              onChange={(event) => setCountryFilter(event.target.value)}
            />
            <Select
              label="Filter by category"
              value={categoryFilter}
              options={[
                { value: "", label: "Todas las categorias" },
                ...SUPPLIER_CATEGORY_OPTIONS.map((option) => ({
                  value: option.value,
                  label: option.label,
                })),
              ]}
              onChange={(event) => setCategoryFilter(event.target.value)}
            />
          </div>
        </section>

        {actionError && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            {actionError}
          </p>
        )}

        {actionFeedback && (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700" aria-live="polite">
            {actionFeedback}
          </p>
        )}

        {isLoading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Loading suppliers...
          </div>
        ) : isError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6">
            <p className="text-sm text-red-700">{error}</p>
            <Button className="mt-4" variant="secondary" onClick={() => void reload()}>
              Retry
            </Button>
          </div>
        ) : filteredSuppliers.length === 0 ? (
          <EmptyState
            title="No suppliers found"
            description="Adjust the filters or create a new supplier to start filling the directory."
            actionLabel="Create supplier"
            onAction={() => setShowCreateForm(true)}
          />
        ) : (
          <div className="grid gap-4">
            {filteredSuppliers.map((supplier) => {
              const rateValue = rateDrafts[supplier.id] ?? String(supplier.monthly_rate);
              const statusValue = statusDrafts[supplier.id] ?? supplier.status;

              return (
                <article
                  key={supplier.id}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-slate-900">{supplier.name}</h3>
                        <SupplierStatusBadge status={supplier.status} />
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        {supplier.country} · {supplier.currency} · {supplier.categories
                          .map((category) => SUPPLIER_CATEGORY_LABELS[category])
                          .join(", ")}
                      </p>
                    </div>
                    <div className="text-sm text-slate-600">
                      <p>Supplier ID: {supplier.id}</p>
                      <p>Last rate update: {formatDate(supplier.updated_at)}</p>
                    </div>
                  </div>

                  <dl className="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
                    <div>
                      <dt className="font-medium text-slate-900">Monthly rate</dt>
                      <dd>{formatMoney(supplier.monthly_rate, supplier.currency)}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-slate-900">Compliance agreement</dt>
                      <dd>{supplier.compliance_agreement ?? "Not set"}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-slate-900">Contract renewal</dt>
                      <dd>{supplier.contract_renewal_date ?? "Not set"}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-slate-900">Contact email</dt>
                      <dd>{supplier.contact_email ?? "Not set"}</dd>
                    </div>
                    <div className="sm:col-span-2 lg:col-span-2">
                      <dt className="font-medium text-slate-900">Notes</dt>
                      <dd>{supplier.notes ?? "No notes"}</dd>
                    </div>
                  </dl>

                  <div className="mt-5 grid gap-4 border-t border-slate-100 pt-4 lg:grid-cols-2">
                    <div className="space-y-3">
                      <h4 className="text-sm font-semibold text-slate-900">Update monthly rate</h4>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                        <Input
                          label="New rate"
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={rateValue}
                          onChange={(event) =>
                            setRateDrafts((current) => ({
                              ...current,
                              [supplier.id]: event.target.value,
                            }))
                          }
                        />
                        <Button
                          disabled={updatingRateId === supplier.id}
                          onClick={() => void handleRateUpdate(supplier)}
                        >
                          {updatingRateId === supplier.id ? "Updating..." : "Update rate"}
                        </Button>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h4 className="text-sm font-semibold text-slate-900">Update status</h4>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                        <Select
                          label="Status"
                          value={statusValue}
                          options={SUPPLIER_STATUS_OPTIONS.map((option) => ({
                            value: option.value,
                            label: option.label,
                          }))}
                          onChange={(event) =>
                            setStatusDrafts((current) => ({
                              ...current,
                              [supplier.id]: event.target.value as SupplierStatus,
                            }))
                          }
                        />
                        <Button
                          variant="secondary"
                          disabled={updatingStatusId === supplier.id}
                          onClick={() => void handleStatusUpdate(supplier)}
                        >
                          {updatingStatusId === supplier.id ? "Updating..." : "Update status"}
                        </Button>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}