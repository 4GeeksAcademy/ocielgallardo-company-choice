import type {
  Company,
  Appointment,
  Invoice,
  NoShowPrediction,
  CriticalFilter,
} from "./models";

const companyOk: Company = {
  id: "c1",
  name: "HealthCore",
  sector: "healthcare",
  reasonForChoosing: "Impacto real",
  vision: "Reducir perdidas",
  portfolioContribution: "Caso end-to-end",
  handlesSensitiveData: true,
};

const appointmentOk: Appointment = {
  appointmentId: "a1",
  patientId: "p1",
  dateISO: "2026-06-12T10:00:00.000Z",
  clinicSite: "Miami",
  country: "US",
  category: "Patient Experience and Access",
  status: "scheduled",
  noShowProbability: 0.42,
};

const invoiceOk: Invoice = {
  invoiceId: "i1",
  patientId: "p1",
  issueDateISO: "2026-06-12",
  category: "Revenue Cycle and Billing",
  status: "submitted",
  amount: 120,
  currency: "USD",
  billingCodes: ["A123"],
  rejectionProbability: 0.1,
};

const predictionOk: NoShowPrediction = {
  predictionId: "n1",
  appointmentId: "a1",
  probability: 0.88,
  criticalThreshold: 0.7,
  isCritical: true,
  recommendedAction: "reminder",
  status: "pending",
};

const filterOk: CriticalFilter = {
  category: "no-show",
  status: "open",
  probabilityRange: { min: 0.7, max: 1 },
  onlyCritical: true,
};

void predictionOk;
void filterOk;

const appointmentBadCountry: Appointment = {
  ...appointmentOk,
  // @ts-expect-error country invalido
  country: "MX",
};

const invoiceBadCategory: Invoice = {
  ...invoiceOk,
  // @ts-expect-error categoria invalida en factura
  category: "Patient Experience and Access",
};

const companyBadName: Company = {
  ...companyOk,
  // @ts-expect-error name debe ser literal HealthCore
  name: "OtraEmpresa",
};

void appointmentBadCountry;
void invoiceBadCategory;
void companyBadName;
