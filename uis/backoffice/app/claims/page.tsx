import { SectionPlaceholder } from "@/components/layout/SectionPlaceholder";

export default function ClaimsPage() {
  return (
    <SectionPlaceholder
      title="Claims"
      description="Claims management placeholder for rejected-claim triage, follow-up tracking, and prevention analytics."
      nextSteps={[
        "Create rejected claims queue with root-cause tags.",
        "Add action timelines for payer follow-up.",
        "Expose recurrence insights to reduce systematic rejection patterns.",
      ]}
    />
  );
}
