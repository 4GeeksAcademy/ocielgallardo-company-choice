import { FLOW_STEPS, KPIS, VALUES } from "@/lib/content";

export function ImpactSection() {
  return (
    <section id="impact" className="mt-12 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand-600)]">
          Operational footprint
        </p>
        <div className="mt-4 grid grid-cols-2 gap-3">
          {KPIS.map((metric) => (
            <article key={metric.label} className="rounded-lg bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">{metric.label}</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{metric.value}</p>
            </article>
          ))}
        </div>

        <div className="mt-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Care flow</h3>
          <ol className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
            {FLOW_STEPS.map((step, index) => (
              <li key={step} className="rounded-md border border-slate-200 bg-white px-3 py-2">
                {index + 1}. {step}
              </li>
            ))}
          </ol>
        </div>
      </div>

      <aside className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Core values</h3>
        <ul className="mt-4 space-y-2 text-sm text-slate-700">
          {VALUES.map((value) => (
            <li key={value} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
              {value}
            </li>
          ))}
        </ul>
      </aside>
    </section>
  );
}
