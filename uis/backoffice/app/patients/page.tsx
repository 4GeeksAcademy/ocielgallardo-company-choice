import { SectionPlaceholder } from "@/components/layout/SectionPlaceholder";

export default function PatientsPage() {
  return (
    <SectionPlaceholder
      title="Patients"
      description="Foundation module for patient registry views, profile search, and compliance-aware patient data access."
      nextSteps={[
        "Add patient directory with clinic and country filters.",
        "Connect patient profile panel with role-based visibility.",
        "Add HIPAA/UK GDPR access-trace markers for sensitive views.",
      ]}
    />
  );
}
