const API_BASE_URL =
  process.env.NEXT_PUBLIC_TRACKER_API_URL ??
  "https://playground.4geeks.com/tracker/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type");
  const body =
    contentType?.includes("application/json")
      ? await response.json()
      : null;

  if (!response.ok) {
    const message =
      (body as { error?: string; detail?: string })?.error ??
      (body as { detail?: string })?.detail ??
      `Error ${response.status}`;
    throw new ApiError(message, response.status, body);
  }

  return body as T;
}
