import { DashboardKpis } from "@/components/dashboard/DashboardKpis";
import { ModuleGrid } from "@/components/dashboard/ModuleGrid";
import { OfficeCharts } from "@/components/dashboard/OfficeCharts";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Today&apos;s overview across clinics, inventory, suppliers, and the platform.
        </p>
      </section>

      <DashboardKpis />
      <OfficeCharts />
      <ModuleGrid />
    </div>
  );
}
