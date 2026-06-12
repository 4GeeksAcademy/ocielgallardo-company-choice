import {
  Appointment,
  CriticalAlert,
  Invoice,
  InvoiceRejectionPrediction,
  NoShowPrediction,
} from "../types/models";

/** Calcula el porcentaje de citas marcadas como no-show. */
export function calculateNoShowRate(appointments: Appointment[]): number {
  if (appointments.length === 0) return 0;
  const noShows = appointments.filter((appointment) => appointment.status === "no-show").length;
  return Number(((noShows / appointments.length) * 100).toFixed(2));
}

/** Calcula el porcentaje de facturas con estado rechazado. */
export function calculateInvoiceRejectionRate(invoices: Invoice[]): number {
  if (invoices.length === 0) return 0;
  const rejected = invoices.filter((invoice) => invoice.status === "rejected").length;
  return Number(((rejected / invoices.length) * 100).toFixed(2));
}

/**
 * Convierte predicciones criticas en alertas operativas.
 * Genera alertas para riesgo de no-show y rechazo de factura.
 */
export function generateCriticalAlerts(
  noShowPredictions: NoShowPrediction[],
  invoiceRejectionPredictions: InvoiceRejectionPrediction[]
): CriticalAlert[] {
  // Alertas generadas desde el flujo de citas.
  const noShowAlerts: CriticalAlert[] = noShowPredictions
    .filter((prediction) => prediction.isCritical)
    .map((prediction) => ({
      alertId: `alert-noshow-${prediction.predictionId}`,
      category: "no-show",
      referenceId: prediction.appointmentId,
      riskLevel: prediction.probability,
      status: "open",
      dateISO: new Date().toISOString(),
    }));

  // Alertas generadas desde el flujo de facturacion.
  const rejectionAlerts: CriticalAlert[] = invoiceRejectionPredictions
    .filter((prediction) => prediction.isCritical)
    .map((prediction) => ({
      alertId: `alert-rejection-${prediction.predictionId}`,
      category: "invoice-rejection",
      referenceId: prediction.invoiceId,
      riskLevel: prediction.probability,
      status: "open",
      dateISO: new Date().toISOString(),
    }));

  return [...noShowAlerts, ...rejectionAlerts];
}

/** Agrupa alertas por estado para simplificar reportes y dashboards. */
export function groupAlertsByStatus(alerts: CriticalAlert[]): Record<string, CriticalAlert[]> {
  return alerts.reduce<Record<string, CriticalAlert[]>>((accumulator, alert) => {
    if (!accumulator[alert.status]) accumulator[alert.status] = [];
    accumulator[alert.status].push(alert);
    return accumulator;
  }, {});
}
