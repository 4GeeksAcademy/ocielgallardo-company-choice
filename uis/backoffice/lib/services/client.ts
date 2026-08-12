import { statusUserMessage } from "@/lib/utils/friendlyApiError";

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

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Could not reach the server. Check your connection and try again.",
      0
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type");
  let body: unknown = null;
  if (contentType?.includes("application/json")) {
    try {
      body = await response.json();
    } catch {
      throw new ApiError(
        statusUserMessage(
          response.status,
          "Received an invalid response from the server."
        ),
        response.status
      );
    }
  }

  if (!response.ok) {
    const message = statusUserMessage(
      response.status,
      "The request could not be completed. Please try again."
    );
    throw new ApiError(message, response.status, body);
  }

  return body as T;
}
