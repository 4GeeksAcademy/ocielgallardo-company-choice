import type {
  Supplier,
  SupplierCreateInput,
  SupplierRateUpdateInput,
  SupplierStatusUpdateInput,
} from "@/types/suppliers";
import {
  HealthcoreApiError,
  healthcoreRequest,
} from "@/lib/services/healthcoreClient";

export { HealthcoreApiError as SupplierApiError };

export function fetchSuppliers(): Promise<Supplier[]> {
  return healthcoreRequest<Supplier[]>("/suppliers");
}

export function createSupplier(input: SupplierCreateInput): Promise<Supplier> {
  return healthcoreRequest<Supplier>("/suppliers", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateSupplierRate(
  id: number,
  input: SupplierRateUpdateInput
): Promise<Supplier> {
  return healthcoreRequest<Supplier>(`/suppliers/${id}/rate`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function updateSupplierStatus(
  id: number,
  input: SupplierStatusUpdateInput
): Promise<Supplier> {
  return healthcoreRequest<Supplier>(`/suppliers/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
