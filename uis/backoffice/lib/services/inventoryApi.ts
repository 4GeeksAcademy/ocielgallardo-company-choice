import type {
  InventoryOrder,
  MedicalSupply,
  MedicalSupplyCreateInput,
  SupplyConsumption,
  SupplyConsumptionCreateInput,
  SupplyDelivery,
  SupplyDeliveryCreateInput,
} from "@/types/inventory";
import {
  HealthcoreApiError,
  healthcoreRequest,
} from "@/lib/services/healthcoreClient";

export { HealthcoreApiError as InventoryApiError };

export function fetchMedicalSupplies(): Promise<MedicalSupply[]> {
  return healthcoreRequest<MedicalSupply[]>("/inventory/products");
}

export function fetchMedicalSupply(id: number): Promise<MedicalSupply> {
  return healthcoreRequest<MedicalSupply>(`/inventory/products/${id}`);
}

export function createMedicalSupply(
  input: MedicalSupplyCreateInput
): Promise<MedicalSupply> {
  return healthcoreRequest<MedicalSupply>("/inventory/products", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createInboundOrder(
  input: SupplyDeliveryCreateInput
): Promise<SupplyDelivery> {
  return healthcoreRequest<SupplyDelivery>("/inventory/orders/inbound", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createOutboundOrder(
  input: SupplyConsumptionCreateInput
): Promise<SupplyConsumption> {
  return healthcoreRequest<SupplyConsumption>("/inventory/orders/outbound", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function fetchInventoryOrders(): Promise<InventoryOrder[]> {
  return healthcoreRequest<InventoryOrder[]>("/inventory/orders");
}

export function friendlyInventoryError(err: unknown, fallback: string): string {
  if (!(err instanceof HealthcoreApiError)) {
    return fallback;
  }
  if (err.status >= 500) {
    return "Algo falló en el servidor. Inténtalo de nuevo en un momento.";
  }
  if (err.status === 404) {
    return "No se encontró el recurso de inventario solicitado.";
  }
  if (err.status === 401 || err.status === 403) {
    return "Tu sesión ha caducado. Vuelve a iniciar sesión.";
  }
  if (err.details && typeof err.details === "object" && "detail" in err.details) {
    const detail = (err.details as { detail: unknown }).detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
      const first = detail[0] as { message?: unknown; msg?: unknown };
      const message = first.message ?? first.msg;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
    if (typeof detail === "string" && detail.trim()) {
      if (/traceback|exception|stack/i.test(detail)) {
        return fallback;
      }
      return detail;
    }
  }
  if (/traceback|exception|stack/i.test(err.message)) {
    return fallback;
  }
  return err.message || fallback;
}
