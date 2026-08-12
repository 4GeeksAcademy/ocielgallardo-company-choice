/**
 * Map API / network errors to stable, user-facing copy.
 * Never forward raw status codes, stack traces, or provider internals.
 */

type StatusfulError = Error & { status?: number; details?: unknown };

function hasStatus(err: unknown): err is StatusfulError {
  return (
    typeof err === "object" &&
    err !== null &&
    "status" in err &&
    typeof (err as { status: unknown }).status === "number"
  );
}

function looksTechnical(text: string): boolean {
  return /traceback|exception|stack|error \d{3}/i.test(text);
}

function firstFieldMessage(details: unknown): string | null {
  if (!details || typeof details !== "object" || !("detail" in details)) {
    return null;
  }
  const detail = (details as { detail: unknown }).detail;
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
    const first = detail[0] as { message?: unknown; msg?: unknown };
    const message = first.message ?? first.msg;
    if (typeof message === "string" && message.trim() && !looksTechnical(message)) {
      return message.trim();
    }
  }
  if (typeof detail === "string" && detail.trim() && !looksTechnical(detail)) {
    // Allow short, known-safe validation strings only (no status codes).
    if (/^error\s+\d{3}$/i.test(detail.trim())) {
      return null;
    }
    return detail.trim();
  }
  return null;
}

export function friendlyApiError(err: unknown, fallback: string): string {
  if (!hasStatus(err)) {
    return fallback;
  }

  const status = err.status ?? 0;

  if (status >= 500) {
    return "Something went wrong on the server. Please try again in a moment.";
  }
  if (status === 404) {
    return "The requested resource was not found.";
  }
  if (status === 401 || status === 403) {
    return "Your session expired. Please sign in again.";
  }
  if (status === 409) {
    return "This record already exists or conflicts with existing data.";
  }

  const fieldMessage = firstFieldMessage(err.details);
  if (fieldMessage) {
    return fieldMessage;
  }

  if (typeof err.message === "string" && err.message.trim()) {
    if (looksTechnical(err.message) || /^error\s+\d{3}$/i.test(err.message.trim())) {
      return fallback;
    }
    return err.message;
  }

  return fallback;
}

/** Spanish variants for auth / profile surfaces. */
export function friendlyApiErrorEs(err: unknown, fallback: string): string {
  if (!hasStatus(err)) {
    return fallback;
  }

  const status = err.status ?? 0;

  if (status >= 500) {
    return "Algo salió mal en el servidor. Inténtalo de nuevo en un momento.";
  }
  if (status === 404) {
    return "No se encontró el recurso solicitado.";
  }
  if (status === 401 || status === 403) {
    return "Tu sesión expiró. Vuelve a iniciar sesión.";
  }
  if (status === 409) {
    return "Este registro ya existe o entra en conflicto con datos existentes.";
  }

  const fieldMessage = firstFieldMessage(err.details);
  if (fieldMessage) {
    return fieldMessage;
  }

  if (typeof err.message === "string" && err.message.trim()) {
    if (looksTechnical(err.message) || /^error\s+\d{3}$/i.test(err.message.trim())) {
      return fallback;
    }
    return err.message;
  }

  return fallback;
}

export function statusUserMessage(status: number, fallback: string): string {
  if (status >= 500) {
    return "Something went wrong on the server. Please try again in a moment.";
  }
  if (status === 404) {
    return "The requested resource was not found.";
  }
  if (status === 401 || status === 403) {
    return "Your session expired. Please sign in again.";
  }
  if (status === 409) {
    return "This record already exists or conflicts with existing data.";
  }
  if (status === 400 || status === 422) {
    return "Some of the submitted data is invalid. Please review and try again.";
  }
  return fallback;
}
