import {
  Appointment,
  Company,
  FocusDepartment,
  Invoice,
  InvoiceRejectionPrediction,
  NoShowPrediction,
  Patient,
  ProjectChallenge,
} from "../types/models";

/** Benchmarks de negocio definidos en CONTEXT.md para HealthCore. */
export const HEALTHCORE_BENCHMARKS: {
  readonly noShowRatePercent: number;
  readonly invoiceRejectionRatePercent: number;
  readonly allowedCountries: readonly ["US", "United Kingdom"];
} = {
  noShowRatePercent: 22,
  invoiceRejectionRatePercent: 14,
  allowedCountries: ["US", "United Kingdom"],
};

/** Valida que un texto requerido no venga vacio. */
function validateRequiredText(value: string, field: string): string[] {
  const errors: string[] = [];
  if (!value.trim()) errors.push(`${field} is required.`);
  return errors;
}

/** Valida que un valor este dentro del rango [min, max]. */
function validateRange(value: number, field: string, min: number, max: number): string[] {
  const errors: string[] = [];
  if (value < min || value > max) errors.push(`${field}: must be between ${min} and ${max}.`);
  return errors;
}

/** Valida que un valor sea exactamente el esperado por regla de negocio. */
function validateExactValue(value: number, expected: number, field: string): string[] {
  const errors: string[] = [];
  if (value !== expected) errors.push(`${field}: must be exactly ${expected}.`);
  return errors;
}

/** Valida que un pais pertenezca al alcance operativo de HealthCore. */
function validateCountryScope(country: Patient["country"]): string[] {
  const errors: string[] = [];
  if (!HEALTHCORE_BENCHMARKS.allowedCountries.includes(country)) {
    errors.push("country: must be US or United Kingdom.");
  }
  return errors;
}

/** Valida consistencia entre pais y moneda de facturacion. */
function validateInvoiceCurrencyByCountry(invoice: Invoice, patientCountry: Patient["country"]): string[] {
  const errors: string[] = [];
  if (patientCountry === "US" && invoice.currency !== "USD") {
    errors.push("currency: for US patients currency must be USD.");
  }
  if (patientCountry === "United Kingdom" && invoice.currency !== "GBP") {
    errors.push("currency: for United Kingdom patients currency must be GBP.");
  }
  return errors;
}

/** Valida que al menos un canal de contacto este presente. */
function validatePatientContactChannels(patient: Patient): string[] {
  const errors: string[] = [];
  const hasPhone: boolean = Boolean(patient.phone && patient.phone.trim());
  const hasEmail: boolean = Boolean(patient.email && patient.email.trim());
  if (!hasPhone && !hasEmail) {
    errors.push("patient: at least one contact channel is required (phone or email).");
  }
  return errors;
}

/** Valida que una probabilidad sea numerica y este en el rango [0, 1]. */
export function validateProbability(value: number, field: string): string[] {
  const errors: string[] = [];
  if (Number.isNaN(value)) errors.push(`${field}: value cannot be NaN.`);
  errors.push(...validateRange(value, field, 0, 1));
  return errors;
}

/** Valida reglas base de Company alineadas a HealthCore. */
export function validateCompany(company: Company): string[] {
  const errors: string[] = [];
  errors.push(...validateRequiredText(company.id, "id"));
  if (company.name !== "HealthCore") errors.push("name: must be HealthCore.");
  if (company.sector !== "healthcare") errors.push("sector: must be healthcare.");
  if (!company.handlesSensitiveData) {
    errors.push("handlesSensitiveData: must be true due to HIPAA/UK GDPR context.");
  }
  return errors;
}

/** Valida reglas de ProjectChallenge segun company-choice/context. */
export function validateProjectChallenge(challenge: ProjectChallenge): string[] {
  const errors: string[] = [];
  errors.push(...validateRequiredText(challenge.id, "id"));
  errors.push(...validateRequiredText(challenge.description, "description"));
  return errors;
}

/**
 * Valida FocusDepartment segun los problemas criticos documentados:
 * - Patient Experience and Access => 22%
 * - Revenue Cycle and Billing => 14%
 */
export function validateFocusDepartment(department: FocusDepartment): string[] {
  const errors: string[] = [];
  errors.push(...validateRequiredText(department.id, "id"));
  errors.push(...validateRequiredText(department.mainProblem, "mainProblem"));
  errors.push(...validateRange(department.currentRatePercentage, "currentRatePercentage", 0, 100));

  if (department.name === "Patient Experience and Access") {
    errors.push(
      ...validateExactValue(
        department.currentRatePercentage,
        HEALTHCORE_BENCHMARKS.noShowRatePercent,
        "currentRatePercentage"
      )
    );
  }

  if (department.name === "Revenue Cycle and Billing") {
    errors.push(
      ...validateExactValue(
        department.currentRatePercentage,
        HEALTHCORE_BENCHMARKS.invoiceRejectionRatePercent,
        "currentRatePercentage"
      )
    );
  }

  return errors;
}

/** Valida reglas de Patient en el alcance operativo de HealthCore. */
export function validatePatient(patient: Patient): string[] {
  const errors: string[] = [];
  errors.push(...validateRequiredText(patient.patientId, "patientId"));
  errors.push(...validateRequiredText(patient.fullName, "fullName"));
  errors.push(...validateRequiredText(patient.medicalHistorySummary, "medicalHistorySummary"));
  errors.push(...validateRequiredText(patient.clinicSite, "clinicSite"));
  errors.push(...validateCountryScope(patient.country));
  errors.push(...validatePatientContactChannels(patient));
  return errors;
}

/** Valida campos minimos requeridos para una cita. */
export function validateAppointment(appointment: Appointment): string[] {
  const errors: string[] = [];
  errors.push(...validateRequiredText(appointment.appointmentId, "appointmentId"));
  errors.push(...validateRequiredText(appointment.patientId, "patientId"));
  errors.push(...validateRequiredText(appointment.dateISO, "dateISO"));
  errors.push(...validateRequiredText(appointment.clinicSite, "clinicSite"));
  errors.push(...validateCountryScope(appointment.country));
  if (appointment.category !== "Patient Experience and Access") {
    errors.push("category: must be Patient Experience and Access.");
  }
  errors.push(...validateProbability(appointment.noShowProbability, "noShowProbability"));
  return errors;
}

/** Valida campos minimos requeridos para una factura. */
export function validateInvoice(invoice: Invoice, patientCountry?: Patient["country"]): string[] {
  const errors: string[] = [];
  errors.push(...validateRequiredText(invoice.invoiceId, "invoiceId"));
  errors.push(...validateRequiredText(invoice.patientId, "patientId"));
  errors.push(...validateRequiredText(invoice.issueDateISO, "issueDateISO"));
  if (invoice.amount <= 0) errors.push("amount must be greater than 0.");
  if (invoice.billingCodes.length === 0) {
    errors.push("billingCodes requires at least one code.");
  }
  if (invoice.category !== "Revenue Cycle and Billing") {
    errors.push("category: must be Revenue Cycle and Billing.");
  }
  errors.push(...validateProbability(invoice.rejectionProbability, "rejectionProbability"));

  // Regla contextual: benchmark de rechazo historico documentado en 14%.
  const benchmarkRate: number = HEALTHCORE_BENCHMARKS.invoiceRejectionRatePercent / 100;
  if (invoice.rejectionProbability < benchmarkRate) {
    errors.push("rejectionProbability: should not be below the 14% baseline from context.");
  }

  if (patientCountry) {
    errors.push(...validateInvoiceCurrencyByCountry(invoice, patientCountry));
  }

  return errors;
}

/**
 * Valida la prediccion de no-show.
 * Regla clave: isCritical debe coincidir con probability >= criticalThreshold.
 */
export function validateNoShowPrediction(prediction: NoShowPrediction): string[] {
  const errors = validateProbability(prediction.probability, "probability");
  errors.push(...validateProbability(prediction.criticalThreshold, "criticalThreshold"));

  // Regla contextual: no-show de red documentado en 22%.
  const noShowBaseline: number = HEALTHCORE_BENCHMARKS.noShowRatePercent / 100;
  if (prediction.criticalThreshold < noShowBaseline) {
    errors.push("criticalThreshold: should be >= 0.22 based on context baseline.");
  }

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

  // Regla contextual: rechazo de red documentado en 14%.
  const rejectionBaseline: number = HEALTHCORE_BENCHMARKS.invoiceRejectionRatePercent / 100;
  if (prediction.criticalThreshold < rejectionBaseline) {
    errors.push("criticalThreshold: should be >= 0.14 based on context baseline.");
  }

  const expected = prediction.probability >= prediction.criticalThreshold;
  if (prediction.isCritical !== expected) {
    errors.push("isCritical must match probability >= criticalThreshold.");
  }

  return errors;
}

/** Valida un registro completo para asegurar reglas antes de procesamiento. */
export function validateRecordBeforeProcessing(params: {
  company?: Company;
  challenge?: ProjectChallenge;
  department?: FocusDepartment;
  patient?: Patient;
  appointment?: Appointment;
  invoice?: Invoice;
  noShowPrediction?: NoShowPrediction;
  invoiceRejectionPrediction?: InvoiceRejectionPrediction;
}): string[] {
  const errors: string[] = [];

  if (params.company) errors.push(...validateCompany(params.company));
  if (params.challenge) errors.push(...validateProjectChallenge(params.challenge));
  if (params.department) errors.push(...validateFocusDepartment(params.department));
  if (params.patient) errors.push(...validatePatient(params.patient));
  if (params.appointment) errors.push(...validateAppointment(params.appointment));
  if (params.invoice) {
    errors.push(...validateInvoice(params.invoice, params.patient?.country));
  }
  if (params.noShowPrediction) {
    errors.push(...validateNoShowPrediction(params.noShowPrediction));
  }
  if (params.invoiceRejectionPrediction) {
    errors.push(...validateInvoiceRejectionPrediction(params.invoiceRejectionPrediction));
  }

  return errors;
}
