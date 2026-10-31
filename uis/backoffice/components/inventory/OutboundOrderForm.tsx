"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { StockLevelBadge } from "@/components/inventory/StockLevelBadge";
import {
  InventoryApiError,
  createOutboundOrder,
  fetchMedicalSupplies,
  friendlyInventoryError,
} from "@/lib/services/inventoryApi";
import { track } from "@/lib/services/telemetry";
import type { ConsumptionType, MedicalSupply } from "@/types/inventory";
import { CONSUMPTION_TYPE_OPTIONS, STOCK_LOW_BELOW } from "@/types/inventory";

interface FormState {
  supply_id: string;
  quantity: string;
  consumption_type: string;
  clinic_id: string;
}

interface FormErrors {
  supply_id?: string;
  quantity?: string;
  consumption_type?: string;
  clinic_id?: string;
}

const emptyForm: FormState = {
  supply_id: "",
  quantity: "",
  consumption_type: "",
  clinic_id: "",
};

const CLINIC_OPTIONS = Array.from({ length: 12 }, (_, index) => {
  const id = index + 1;
  return { value: String(id), label: `Clinic ${id}` };
});

function isConsumptionType(value: string): value is ConsumptionType {
  return value === "clinical_use" || value === "expiry_waste";
}

function validate(values: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!values.supply_id) {
    errors.supply_id = "Select a supply.";
  }
  const quantity = Number(values.quantity);
  if (!values.quantity.trim()) {
    errors.quantity = "Quantity is required.";
  } else if (!Number.isInteger(quantity) || quantity <= 0) {
    errors.quantity = "Enter a whole number greater than 0.";
  }
  if (!values.consumption_type) {
    errors.consumption_type = "Select the usage type.";
  } else if (!isConsumptionType(values.consumption_type)) {
    errors.consumption_type = "Type must be clinical use or expired / waste.";
  }
  const clinicId = Number(values.clinic_id);
  if (!values.clinic_id) {
    errors.clinic_id = "Select a clinic.";
  } else if (!Number.isInteger(clinicId) || clinicId < 1 || clinicId > 12) {
    errors.clinic_id = "Clinic must be between 1 and 12.";
  }
  return errors;
}

export function OutboundOrderForm() {
  const searchParams = useSearchParams();
  const preselectedSupplyId = searchParams.get("supply_id") ?? "";

  const [supplies, setSupplies] = useState<MedicalSupply[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoadingSupplies, setIsLoadingSupplies] = useState(true);

  const [values, setValues] = useState<FormState>({
    ...emptyForm,
    supply_id: preselectedSupplyId,
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const submittedRef = useRef(false);

  /* ── inventory_form_started / abandoned ──────────────────────── */
  useEffect(() => {
    track("inventory_form_started", { form_name: "outbound" });
    return () => {
      if (!submittedRef.current) {
        const filled = Object.values(values).filter((v) => v.trim() !== "").length;
        track("inventory_form_abandoned", {
          form_name: "outbound",
          fields_filled: filled,
        });
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSupplies = useCallback(async () => {
    setIsLoadingSupplies(true);
    setLoadError(null);
    try {
      const data = await fetchMedicalSupplies();
      setSupplies(data);
    } catch (err) {
      setLoadError(
        friendlyInventoryError(
          err,
          "Could not load supplies. Check that the API is running."
        )
      );
    } finally {
      setIsLoadingSupplies(false);
    }
  }, []);

  useEffect(() => {
    void loadSupplies();
  }, [loadSupplies]);

  useEffect(() => {
    if (!preselectedSupplyId) {
      return;
    }
    setValues((current) =>
      current.supply_id ? current : { ...current, supply_id: preselectedSupplyId }
    );
  }, [preselectedSupplyId]);

  const selectedSupply = useMemo(
    () => supplies.find((supply) => String(supply.id) === values.supply_id) ?? null,
    [supplies, values.supply_id]
  );

  const quantityExceedsStock = useMemo(() => {
    if (!selectedSupply || !values.quantity.trim()) {
      return false;
    }
    const quantity = Number(values.quantity);
    return Number.isInteger(quantity) && quantity > selectedSupply.current_stock;
  }, [selectedSupply, values.quantity]);

  const supplyOptions = useMemo(
    () => [
      { value: "", label: "Select a supply" },
      ...supplies.map((supply) => ({
        value: String(supply.id),
        label: `${supply.name} (${supply.sku})`,
      })),
    ],
    [supplies]
  );

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    if (key === "quantity") {
      setErrors((current) => {
        if (!current.quantity) {
          return current;
        }
        const next = { ...current };
        delete next.quantity;
        return next;
      });
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const nextErrors = validate(values);
    if (!nextErrors.quantity && selectedSupply) {
      const requested = Number(values.quantity);
      const available = Math.max(selectedSupply.current_stock, 0);
      if (requested > available) {
        nextErrors.quantity =
          available === 0
            ? "No stock available for this supply."
            : `Insufficient stock: only ${available} available.`;
      }
    }
    setErrors(nextErrors);
    setSuccessMessage(null);
    setSubmitError(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    if (!isConsumptionType(values.consumption_type)) {
      return;
    }

    setIsSubmitting(true);
    const qty = Number(values.quantity);
    const clinicId = Number(values.clinic_id);
    const productId = Number(values.supply_id);
    try {
      await createOutboundOrder({
        supply_id: productId,
        quantity: qty,
        consumption_type: values.consumption_type,
        clinic_id: clinicId,
      });

      submittedRef.current = true;
      track("outbound_order_created", {
        clinic_id: clinicId,
        country: selectedSupply?.country ?? "US",
        product_id: productId,
        product_category: selectedSupply?.category ?? "consumables",
        quantity: qty,
        department: values.consumption_type,
        consumption_type: values.consumption_type,
      });

      if (selectedSupply) {
        const remainingStock = selectedSupply.current_stock - qty;
        if (remainingStock < STOCK_LOW_BELOW) {
          track("stock_threshold_triggered", {
            clinic_id: clinicId,
            country: selectedSupply.country,
            product_id: productId,
            product_category: selectedSupply.category,
            quantity: remainingStock,
            current_stock: remainingStock,
            min_stock_threshold: STOCK_LOW_BELOW,
          });
        }
      }

      setValues(emptyForm);
      setErrors({});
      setSuccessMessage("Usage logged.");
      await loadSupplies();
    } catch (err) {
      track("outbound_order_rejected", {
        http_status: err instanceof InventoryApiError ? err.status : 0,
        rejection_reason: friendlyInventoryError(err, "unknown"),
      });
      const message = friendlyInventoryError(
        err,
        "Could not log the usage. Check the details and try again."
      );
      if (
        err instanceof InventoryApiError &&
        (err.status === 400 || err.status === 409 || err.status === 422)
      ) {
        setErrors((current) => ({ ...current, quantity: message }));
        return;
      }
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      {isLoadingSupplies && (
        <p className="text-sm text-slate-600 dark:text-slate-300">Loading supplies…</p>
      )}

      {loadError && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-800"
        >
          <p>{loadError}</p>
          <Button
            type="button"
            variant="secondary"
            className="mt-3 text-xs"
            onClick={() => void loadSupplies()}
          >
            Retry
          </Button>
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
        >
          {successMessage}
        </div>
      )}

      {submitError && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-800"
        >
          {submitError}
        </div>
      )}

      <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
        <div className="space-y-1.5">
          <Select
            label="Supply"
            name="supply_id"
            options={supplyOptions}
            value={values.supply_id}
            onChange={(event) => updateField("supply_id", event.target.value)}
            disabled={isLoadingSupplies || Boolean(loadError)}
            required
          />
          {errors.supply_id && (
            <p className="text-sm text-red-600 dark:text-red-400" role="alert">
              {errors.supply_id}
            </p>
          )}
        </div>

        {selectedSupply && (
          <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Available stock
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <p className="text-sm text-slate-700 dark:text-slate-200">
                {selectedSupply.name} ({selectedSupply.sku})
              </p>
              <StockLevelBadge currentStock={selectedSupply.current_stock} />
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <Input
            label="Quantity"
            name="quantity"
            type="number"
            min={1}
            max={
              selectedSupply
                ? Math.max(selectedSupply.current_stock, 0)
                : undefined
            }
            step={1}
            value={values.quantity}
            onChange={(event) => updateField("quantity", event.target.value)}
            error={errors.quantity}
            required
          />
          {quantityExceedsStock && !errors.quantity && (
            <p className="text-sm text-red-600 dark:text-red-400" role="alert">
              The quantity exceeds available stock (
              {Math.max(selectedSupply?.current_stock ?? 0, 0)}). Reduce it to
              log this usage.
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Select
            label="Usage type"
            name="consumption_type"
            options={[
              { value: "", label: "Select the usage type" },
              ...CONSUMPTION_TYPE_OPTIONS,
            ]}
            value={values.consumption_type}
            onChange={(event) =>
              updateField("consumption_type", event.target.value)
            }
            required
          />
          {errors.consumption_type && (
            <p className="text-sm text-red-600 dark:text-red-400" role="alert">
              {errors.consumption_type}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Select
            label="Clinic"
            name="clinic_id"
            options={[
              { value: "", label: "Select a clinic (1–12)" },
              ...CLINIC_OPTIONS,
            ]}
            value={values.clinic_id}
            onChange={(event) => updateField("clinic_id", event.target.value)}
            required
          />
          {errors.clinic_id && (
            <p className="text-sm text-red-600 dark:text-red-400" role="alert">
              {errors.clinic_id}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button
            type="submit"
            disabled={
              isSubmitting ||
              isLoadingSupplies ||
              Boolean(loadError) ||
              quantityExceedsStock
            }
          >
            {isSubmitting ? "Logging…" : "Log usage"}
          </Button>
          <Link
            href="/inventory/products"
            className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
          >
            Back to supplies
          </Link>
        </div>
      </form>
    </div>
  );
}
