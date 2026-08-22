import type {
  Supplier,
  SupplierCreateInput,
  SupplierRateUpdateInput,
  SupplierStatusUpdateInput,
} from "@/types/suppliers";

const HEALTHCORE_API_BASE_URL =
  process.env.NEXT_PUBLIC_HEALTHCORE_API_URL ?? "http://127.0.0.1:8000";

export class SupplierApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "SupplierApiError";
  }
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item)
        )
        .join("; ");
    }
  }
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${HEALTHCORE_API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const contentType = response.headers.get("content-type");
  const body = contentType?.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw new SupplierApiError(
      extractDetail(body, `Error ${response.status}`),
      response.status,
      body
    );
  }

  return body as T;
}

export function fetchSuppliers(): Promise<Supplier[]> {
  return request<Supplier[]>("/suppliers");
}

export function createSupplier(input: SupplierCreateInput): Promise<Supplier> {
  return request<Supplier>("/suppliers", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateSupplierRate(
  id: number,
  input: SupplierRateUpdateInput
): Promise<Supplier> {
  return request<Supplier>(`/suppliers/${id}/rate`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function updateSupplierStatus(
  id: number,
  input: SupplierStatusUpdateInput
): Promise<Supplier> {
  return request<Supplier>(`/suppliers/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}