export type SupplierCountry = "USA" | "UK";
export type SupplierCurrency = "USD" | "GBP";
export type SupplierStatus = "active" | "suspended";
export type ComplianceAgreement = "BAA" | "DPA" | "both";

export type SupplierCategory =
  | "medical_supplies"
  | "laboratory_services"
  | "pharmaceutical"
  | "clinical_software"
  | "it_infrastructure"
  | "hr_and_payroll_software"
  | "cleaning_and_facilities"
  | "patient_communication"
  | "billing_and_coding_software"
  | "training_platforms";

export interface Supplier {
  id: number;
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  monthly_rate: number;
  currency: SupplierCurrency;
  updated_at: string | null;
  status: SupplierStatus;
  compliance_agreement: ComplianceAgreement | null;
  contract_renewal_date: string | null;
  contact_email: string | null;
  notes: string | null;
}

export interface SupplierCreateInput {
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  monthly_rate: number;
  currency: SupplierCurrency;
  status: SupplierStatus;
  compliance_agreement: ComplianceAgreement | null;
  contract_renewal_date: string | null;
  contact_email: string | null;
  notes: string | null;
}

export interface SupplierRateUpdateInput {
  monthly_rate: number;
}

export interface SupplierStatusUpdateInput {
  status: SupplierStatus;
}

export const SUPPLIER_COUNTRY_OPTIONS = [
  { value: "", label: "Todos los paises" },
  { value: "USA", label: "USA" },
  { value: "UK", label: "UK" },
] as const;

export const SUPPLIER_STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "suspended", label: "Suspended" },
] as const;

export const SUPPLIER_CATEGORY_OPTIONS: Array<{
  value: SupplierCategory;
  label: string;
}> = [
  { value: "medical_supplies", label: "Medical supplies" },
  { value: "laboratory_services", label: "Laboratory services" },
  { value: "pharmaceutical", label: "Pharmaceutical" },
  { value: "clinical_software", label: "Clinical software" },
  { value: "it_infrastructure", label: "IT infrastructure" },
  { value: "hr_and_payroll_software", label: "HR and payroll software" },
  { value: "cleaning_and_facilities", label: "Cleaning and facilities" },
  { value: "patient_communication", label: "Patient communication" },
  { value: "billing_and_coding_software", label: "Billing and coding software" },
  { value: "training_platforms", label: "Training platforms" },
];

export const SUPPLIER_CATEGORY_LABELS: Record<SupplierCategory, string> =
  Object.fromEntries(
    SUPPLIER_CATEGORY_OPTIONS.map((option) => [option.value, option.label])
  ) as Record<SupplierCategory, string>;

export const SUPPLIER_STATUS_BADGE_CLASSES: Record<SupplierStatus, string> = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  suspended: "bg-amber-50 text-amber-700 ring-amber-600/20",
};

export const SUPPLIER_STATUS_LABELS: Record<SupplierStatus, string> = {
  active: "Active",
  suspended: "Suspended",
};

export function currencyForCountry(country: SupplierCountry): SupplierCurrency {
  return country === "USA" ? "USD" : "GBP";
}