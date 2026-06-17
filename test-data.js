// Datos de prueba aislados para la interfaz manual de test.
// No forman parte de la logica de negocio del proyecto.

export const samplePatients = [
  {
    patientId: "pat-001",
    fullName: "Ana Gomez",
    phone: "+1-202-555-0101",
    email: "ana.gomez@example.com",
    medicalHistorySummary: "Type 2 diabetes with controlled HbA1c.",
    clinicSite: "Boston Central",
    country: "US",
    status: "active"
  },
  {
    patientId: "pat-002",
    fullName: "Liam Carter",
    phone: "+44-20-7000-1102",
    email: "liam.carter@example.co.uk",
    medicalHistorySummary: "Hypertension under periodic follow-up.",
    clinicSite: "London West",
    country: "United Kingdom",
    status: "active"
  },
  {
    patientId: "pat-003",
    fullName: "Mia Lewis",
    phone: "",
    email: "",
    medicalHistorySummary: "Asthma, seasonal exacerbations.",
    clinicSite: "Austin North",
    country: "US",
    status: "inactive"
  }
];

export const sampleAppointments = [
  {
    appointmentId: "apt-101",
    patientId: "pat-001",
    dateISO: "2026-06-20T10:30:00.000Z",
    clinicSite: "Boston Central",
    country: "US",
    category: "Patient Experience and Access",
    status: "no-show",
    noShowProbability: 0.78
  },
  {
    appointmentId: "apt-102",
    patientId: "pat-002",
    dateISO: "2026-06-21T11:00:00.000Z",
    clinicSite: "London West",
    country: "United Kingdom",
    category: "Patient Experience and Access",
    status: "completed",
    noShowProbability: 0.18
  },
  {
    appointmentId: "apt-103",
    patientId: "pat-003",
    dateISO: "2026-06-22T09:00:00.000Z",
    clinicSite: "Austin North",
    country: "US",
    category: "Patient Experience and Access",
    status: "confirmed",
    noShowProbability: 0.52
  }
];

export const sampleInvoices = [
  {
    invoiceId: "inv-201",
    patientId: "pat-001",
    issueDateISO: "2026-06-05T00:00:00.000Z",
    category: "Revenue Cycle and Billing",
    status: "rejected",
    amount: 1200,
    currency: "USD",
    billingCodes: ["A100", "B220"],
    rejectionProbability: 0.64
  },
  {
    invoiceId: "inv-202",
    patientId: "pat-002",
    issueDateISO: "2026-06-06T00:00:00.000Z",
    category: "Revenue Cycle and Billing",
    status: "accepted",
    amount: 840,
    currency: "GBP",
    billingCodes: ["C010"],
    rejectionProbability: 0.21
  },
  {
    invoiceId: "inv-203",
    patientId: "pat-003",
    issueDateISO: "2026-06-07T00:00:00.000Z",
    category: "Revenue Cycle and Billing",
    status: "submitted",
    amount: 420,
    currency: "USD",
    billingCodes: ["D300", "D301"],
    rejectionProbability: 0.33
  }
];

export const sampleNoShowPredictions = [
  {
    predictionId: "ns-001",
    appointmentId: "apt-101",
    probability: 0.78,
    criticalThreshold: 0.45,
    isCritical: true,
    recommendedAction: "reminder",
    status: "pending"
  },
  {
    predictionId: "ns-002",
    appointmentId: "apt-102",
    probability: 0.18,
    criticalThreshold: 0.45,
    isCritical: false,
    recommendedAction: "confirmation",
    status: "actioned"
  },
  {
    predictionId: "ns-003",
    appointmentId: "apt-103",
    probability: 0.52,
    criticalThreshold: 0.45,
    isCritical: true,
    recommendedAction: "reschedule",
    status: "pending"
  }
];

export const sampleInvoiceRejectionPredictions = [
  {
    predictionId: "ir-001",
    invoiceId: "inv-201",
    probability: 0.64,
    criticalThreshold: 0.35,
    isCritical: true,
    recommendedAction: "validate",
    status: "pending"
  },
  {
    predictionId: "ir-002",
    invoiceId: "inv-202",
    probability: 0.21,
    criticalThreshold: 0.35,
    isCritical: false,
    recommendedAction: "submit",
    status: "actioned"
  },
  {
    predictionId: "ir-003",
    invoiceId: "inv-203",
    probability: 0.33,
    criticalThreshold: 0.35,
    isCritical: false,
    recommendedAction: "correct",
    status: "discarded"
  }
];

export const sampleClaims = [];
