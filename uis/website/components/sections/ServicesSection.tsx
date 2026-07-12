import { SERVICES } from "@/lib/content";

export function ServicesSection() {
  return (
    <section id="services" className="mt-12">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand-600)]">
          Services
        </p>
        <h2 className="mt-2 text-2xl font-bold text-slate-900 sm:text-3xl">What HealthCore is improving now</h2>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {SERVICES.map((service) => (
          <article key={service.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">{service.title}</h3>
            <p className="mt-2 text-sm text-slate-600">{service.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
