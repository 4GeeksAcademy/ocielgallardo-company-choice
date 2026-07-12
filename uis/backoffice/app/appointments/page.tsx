import { SectionPlaceholder } from "@/components/layout/SectionPlaceholder";

export default function AppointmentsPage() {
  return (
    <SectionPlaceholder
      title="Appointments"
      description="Operational module placeholder for schedule management, no-show prevention workflows, and clinic throughput visibility."
      nextSteps={[
        "Add appointment board by site and status.",
        "Integrate no-show prediction prioritization queue.",
        "Enable reminder and reschedule actions for high-risk appointments.",
      ]}
    />
  );
}
