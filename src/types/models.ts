/** Departamentos clave seleccionados para el proyecto. */
export type DepartmentName =
  | "Patient Experience and Access"
  | "Revenue Cycle and Billing";

/** Estados de avance del reto principal. */
export type ChallengeStatus = "pending" | "in-progress" | "completed";

/** Estados posibles de una cita. */
export type AppointmentStatus =
  | "scheduled"
  | "confirmed"
  | "canceled"
  | "no-show"
  | "completed";

/** Estados posibles de una factura en el ciclo de ingresos. */
export type InvoiceStatus =
  | "draft"
  | "submitted"
  | "accepted"
  | "rejected"
  | "paid";

/** Estado operativo de una prediccion de IA. */
export type PredictionStatus = "pending" | "actioned" | "discarded";

/** Categorias de riesgo critico monitoreadas por el proyecto. */
export type RiskCategory = "no-show" | "invoice-rejection";

/** Datos base de la empresa seleccionada. */
export interface Company {
  id: string;
  name: "HealthCore";
  sector: "healthcare";
  reasonForChoosing: string;
  vision: string;
  portfolioContribution: string;
  handlesSensitiveData: true;
}

/** Departamento de enfoque y su metrica principal. */
export interface FocusDepartment {
  id: string;
  name: DepartmentName;
  mainProblem: string;
  currentRatePercentage: number;
}

/** Definicion del reto central del proyecto. */
export interface ProjectChallenge {
  id: string;
  description: "Intelligent system that predicts revenue losses and acts automatically to prevent them.";
  status: ChallengeStatus;
}

/** Datos minimos del paciente para predicciones operativas. */
export interface Patient {
  patientId: string;
  fullName: string;
  phone?: string;
  email?: string;
  medicalHistorySummary: string;
  clinicSite: string;
  country: "US" | "United Kingdom";
  status: "active" | "inactive";
}

/** Cita usada para modelar riesgo de no-show. */
export interface Appointment {
  appointmentId: string;
  patientId: string;
  dateISO: string;
  clinicSite: string;
  country: "US" | "United Kingdom";
  category: "Patient Experience and Access";
  status: AppointmentStatus;
  noShowProbability: number;
}

/** Factura usada para modelar riesgo de rechazo. */
export interface Invoice {
  invoiceId: string;
  patientId: string;
  issueDateISO: string;
  category: "Revenue Cycle and Billing";
  status: InvoiceStatus;
  amount: number;
  currency: "USD" | "GBP";
  billingCodes: string[];
  rejectionProbability: number;
}

/** Prediccion realizada antes de la cita para prevenir no-shows. */
export interface NoShowPrediction {
  predictionId: string;
  appointmentId: string;
  probability: number;
  criticalThreshold: number;
  isCritical: boolean;
  recommendedAction: "reminder" | "confirmation" | "reschedule";
  status: PredictionStatus;
}

/** Prediccion realizada antes de enviar la factura para prevenir rechazos. */
export interface InvoiceRejectionPrediction {
  predictionId: string;
  invoiceId: string;
  probability: number;
  criticalThreshold: number;
  isCritical: boolean;
  recommendedAction: "validate" | "correct" | "submit";
  status: PredictionStatus;
}

/** Alerta operacional creada cuando una prediccion supera el umbral critico. */
export interface CriticalAlert {
  alertId: string;
  category: RiskCategory;
  referenceId: string;
  riskLevel: number;
  status: "open" | "in-progress" | "closed";
  dateISO: string;
}

/** Rango numerico usado en filtros de probabilidad. */
export interface NumericRange {
  min?: number;
  max?: number;
}

/** Filtros combinables para consultas de elementos criticos. */
export interface CriticalFilter {
  category?: string;
  status?: string;
  probabilityRange?: NumericRange;
  onlyCritical?: boolean;
}
