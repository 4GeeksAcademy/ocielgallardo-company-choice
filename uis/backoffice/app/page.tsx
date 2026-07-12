import Link from "next/link";
import { Hito2Playground } from "@/components/dashboard/Hito2Playground";

const MODULES = [
  {
    href: "/patients",
    title: "Patients",
    description: "Patient record navigation and validation workflows.",
  },
  {
    href: "/appointments",
    title: "Appointments",
    description: "Schedule visibility and no-show risk exploration.",
  },
  {
    href: "/billing",
    title: "Billing",
    description: "Revenue-cycle quality checks and invoice controls.",
  },
  {
    href: "/claims",
    title: "Claims",
    description: "Claim rejection analysis and prevention pathways.",
  },
  {
    href: "/reports",
    title: "Reports",
    description: "Operational and executive metrics by domain.",
  },
  {
    href: "/applications",
    title: "People & Talent",
    description: "Candidate pipeline tracker integrated with external API.",
  },
] as const;

export default function HomePage() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          HealthCore Internal Workspace
        </p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900 sm:text-3xl">
          Backoffice Dashboard
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600 sm:text-base">
          Unified internal console for operational teams. This first release keeps
          the existing People & Talent tracker and exposes Hito 2 business logic
          demos from the shared TypeScript domain utilities.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {MODULES.map((module) => (
          <Link
            key={module.href}
            href={module.href}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow"
          >
            <h2 className="text-base font-semibold text-slate-900">{module.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{module.description}</p>
          </Link>
        ))}
      </section>

      <Hito2Playground />
    </div>
  );
}
