import { SectionPlaceholder } from "@/components/layout/SectionPlaceholder";

export default function ReportsPage() {
  return (
    <SectionPlaceholder
      title="Reports"
      description="Executive and department reporting module placeholder for KPI rollups and scheduled analytics deliveries."
      nextSteps={[
        "Define KPI panels for no-show, rejection, and utilization rates.",
        "Add weekly automated summary generation hooks.",
        "Provide threshold alerts for critical operational metrics.",
      ]}
    />
  );
}
