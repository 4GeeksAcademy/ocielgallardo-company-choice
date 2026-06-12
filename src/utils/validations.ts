import {
  Appointment,
  Invoice,
  InvoiceRejectionPrediction,
  NoShowPrediction,
} from "../types/models";

/** Valida que una probabilidad sea numerica y este en el rango [0, 1]. */
export function validateProbability(value: number, field: string): string[] {
  const errors: string[] = [];
  if (Number.isNaN(value)) errors.push(`${field}: value cannot be NaN.`);
  if (value < 0 || value > 1) errors.push(`${field}: must be between 0 and 1.`);
  return errors;
}

/** Valida campos minimos requeridos para una cita. */
export function validateAppointment(appointment: Appointment): string[] {
  const errors: string[] = [];
  if (!appointment.appointmentId.trim()) errors.push("appointmentId is required.");
  if (!appointment.patientId.trim()) errors.push("patientId is required.");
  if (!appointment.dateISO.trim()) errors.push("dateISO is required.");
  errors.push(...validateProbability(appointment.noShowProbability, "noShowProbability"));
  return errors;
}

/** Valida campos minimos requeridos para una factura. */
export function validateInvoice(invoice: Invoice): string[] {
  const errors: string[] = [];
  if (!invoice.invoiceId.trim()) errors.push("invoiceId is required.");
  if (!invoice.patientId.trim()) errors.push("patientId is required.");
  if (invoice.amount <= 0) errors.push("amount must be greater than 0.");
  if (invoice.billingCodes.length === 0) {
    errors.push("billingCodes requires at least one code.");
  }
  errors.push(...validateProbability(invoice.rejectionProbability, "rejectionProbability"));
  return errors;
}

/**
 * Valida la prediccion de no-show.
 * Regla clave: isCritical debe coincidir con probability >= criticalThreshold.
 */
export function validateNoShowPrediction(prediction: NoShowPrediction): string[] {
  const errors = validateProbability(prediction.probability, "probability");
  errors.push(...validateProbability(prediction.criticalThreshold, "criticalThreshold"));

  const expected = prediction.probability >= prediction.criticalThreshold;
  if (prediction.isCritical !== expected) {
    errors.push("isCritical must match probability >= criticalThreshold.");
  }

  return errors;
}

/**
 * Valida la prediccion de rechazo de factura.
 * Regla clave: isCritical debe coincidir con probability >= criticalThreshold.
 */
export function validateInvoiceRejectionPrediction(
  prediction: InvoiceRejectionPrediction
): string[] {
  const errors = validateProbability(prediction.probability, "probability");
  errors.push(...validateProbability(prediction.criticalThreshold, "criticalThreshold"));

  const expected = prediction.probability >= prediction.criticalThreshold;
  if (prediction.isCritical !== expected) {
    errors.push("isCritical must match probability >= criticalThreshold.");
  }

  return errors;
}
