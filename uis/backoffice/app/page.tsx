import dynamic from "next/dynamic";
import Link from "next/link";

const Hito2Playground = dynamic(
  () =>
    import("@/components/dashboard/Hito2Playground").then((mod) => ({
      default: mod.Hito2Playground,
    })),
  {
    loading: () => (
      <section
        className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm sm:p-6"
        aria-busy="true"
      >
        Loading Hito 2 playground…
      </section>
    ),
  },
);

const MODULES = [
  {
    href: "/incidents",
    title: "Incidents",
    description: "Register, filter, and update incident status across clinics.",
  },
  {
    href: "/incidents/summary",
    title: "Incident summary",
    description: "Aggregated metrics by status, category, origin, and branch.",
  },
  {
    href: "/suppliers",
    title: "Suppliers",
    description: "Supplier directory with filters, rates, and status controls.",
  },
  {
    href: "/inventory/products",
    title: "Suministros",
    description: "Medical supplies list with current stock and level badges.",
  },
  {
    href: "/inventory/orders",
    title: "Historial de órdenes",
    description: "Inbound deliveries and outbound consumption history.",
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
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
          HealthCore Internal Workspace
        </p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-50 sm:text-3xl">
          Backoffice Dashboard
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          Internal console for incidents, suppliers, inventory, and People &amp;
          Talent. Hito 2 domain utilities remain available below for interactive
          demos.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {MODULES.map((module) => (
          <Link
            key={module.href}
            href={module.href}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-500"
          >
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-50">{module.title}</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{module.description}</p>
          </Link>
        ))}
      </section>

      <Hito2Playground />
    </div>
  );
}
