"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  InventoryApiError,
  createInboundOrder,
  fetchMedicalSupplies,
  friendlyInventoryError,
} from "@/lib/services/inventoryApi";
import { track } from "@/lib/services/telemetry";
import type { MedicalSupply } from "@/types/inventory";

interface FormState {
  supply_id: string;
  quantity: string;
  vendor_name: string;
  clinic_id: string;
}

interface FormErrors {
  supply_id?: string;
  quantity?: string;
  vendor_name?: string;
  clinic_id?: string;
}

const emptyForm: FormState = {
  supply_id: "",
  quantity: "",
  vendor_name: "",
  clinic_id: "",
};

const CLINIC_OPTIONS = Array.from({ length: 12 }, (_, index) => {
  const id = index + 1;
  return { value: String(id), label: `Clínica ${id}` };
});

function validate(values: FormState): FormErrors {
  const errors: FormErrors = {};
  if (!values.supply_id) {
    errors.supply_id = "Selecciona un suministro.";
  }
  const quantity = Number(values.quantity);
  if (!values.quantity.trim()) {
    errors.quantity = "La cantidad es obligatoria.";
  } else if (!Number.isInteger(quantity) || quantity <= 0) {
    errors.quantity = "Introduce un entero mayor que 0.";
  }
  if (!values.vendor_name.trim()) {
    errors.vendor_name = "El nombre del proveedor es obligatorio.";
  }
  const clinicId = Number(values.clinic_id);
  if (!values.clinic_id) {
    errors.clinic_id = "Selecciona una clínica.";
  } else if (!Number.isInteger(clinicId) || clinicId < 1 || clinicId > 12) {
    errors.clinic_id = "La clínica debe estar entre 1 y 12.";
  }
  return errors;
}

export function InboundOrderForm() {
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
    track("inventory_form_started", { form_name: "inbound" });
    return () => {
      if (!submittedRef.current) {
        const filled = Object.values(values).filter((v) => v.trim() !== "").length;
        track("inventory_form_abandoned", {
          form_name: "inbound",
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
          "No se pudieron cargar los suministros. Comprueba que la API esté en marcha."
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

  const supplyOptions = useMemo(
    () => [
      { value: "", label: "Selecciona un suministro" },
      ...supplies.map((supply) => ({
        value: String(supply.id),
        label: `${supply.name} (${supply.sku})`,
      })),
    ],
    [supplies]
  );

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const nextErrors = validate(values);
    setErrors(nextErrors);
    setSuccessMessage(null);
    setSubmitError(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    const selectedSupply = supplies.find(
      (s) => String(s.id) === values.supply_id
    );
    try {
      await createInboundOrder({
        supply_id: Number(values.supply_id),
        quantity: Number(values.quantity),
        vendor_name: values.vendor_name.trim(),
        clinic_id: Number(values.clinic_id),
      });

      submittedRef.current = true;
      track("inbound_order_created", {
        clinic_id: Number(values.clinic_id),
        country: selectedSupply?.country ?? "US",
        product_id: Number(values.supply_id),
        product_category: selectedSupply?.category ?? "consumables",
        quantity: Number(values.quantity),
        vendor_name: values.vendor_name.trim(),
      });

      setValues(emptyForm);
      setErrors({});
      setSuccessMessage("Entrega registrada correctamente.");
    } catch (err) {
      track("inbound_order_rejected", {
        http_status: err instanceof InventoryApiError ? err.status : 0,
        rejection_reason: friendlyInventoryError(err, "unknown"),
      });
      setSubmitError(
        friendlyInventoryError(
          err,
          "No se pudo registrar la entrega. Revisa los datos e inténtalo de nuevo."
        )
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      {isLoadingSupplies && (
        <p className="text-sm text-slate-600 dark:text-slate-300">Cargando suministros…</p>
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
            Reintentar
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
            label="Suministro"
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

        <Input
          label="Cantidad"
          name="quantity"
          type="number"
          min={1}
          step={1}
          value={values.quantity}
          onChange={(event) => updateField("quantity", event.target.value)}
          error={errors.quantity}
          required
        />

        <Input
          label="Proveedor"
          name="vendor_name"
          value={values.vendor_name}
          onChange={(event) => updateField("vendor_name", event.target.value)}
          error={errors.vendor_name}
          placeholder="Ej. MedLine Industries"
          required
        />

        <div className="space-y-1.5">
          <Select
            label="Clínica"
            name="clinic_id"
            options={[
              { value: "", label: "Selecciona una clínica (1–12)" },
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
          <Button type="submit" disabled={isSubmitting || isLoadingSupplies || Boolean(loadError)}>
            {isSubmitting ? "Registrando…" : "Registrar entrega"}
          </Button>
          <Link
            href="/inventory/products"
            className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
          >
            Volver a suministros
          </Link>
        </div>
      </form>
    </div>
  );
}
