export const SITE_COPY = {
  brand: "HealthCore",
  tagline: "Intelligent, secure, and human outpatient care.",
  summary:
    "HealthCore operates 12 clinics across the US and UK and is modernizing patient access, clinical workflows, billing quality, and compliance operations.",
};

export const SERVICES = [
  {
    title: "Primary and preventive care",
    text: "Same-day care access, chronic condition follow-up, and preventive programs across all clinics.",
  },
  {
    title: "Patient access optimization",
    text: "Unified scheduling and proactive no-show prevention strategy for better attendance outcomes.",
  },
  {
    title: "Revenue cycle intelligence",
    text: "Data-assisted coding and rejection prevention targeting the current 14% denial baseline.",
  },
  {
    title: "Compliance operations",
    text: "HIPAA and UK GDPR aligned workflows with auditable data access and governance controls.",
  },
] as const;

export const KPIS = [
  { label: "Clinics", value: "12" },
  { label: "Employees", value: "200+" },
  { label: "No-show baseline", value: "22%" },
  { label: "Claim rejection baseline", value: "14%" },
] as const;

export const FLOW_STEPS = [
  "Book appointment",
  "Risk and eligibility checks",
  "Clinical encounter",
  "Billing and follow-up",
] as const;

export const VALUES = [
  "Patient trust",
  "Operational reliability",
  "Data protection by design",
  "Evidence-based decisions",
] as const;
