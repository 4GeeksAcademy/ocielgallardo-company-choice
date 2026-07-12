interface SectionPlaceholderProps {
  title: string;
  description: string;
  nextSteps: string[];
}

export function SectionPlaceholder({
  title,
  description,
  nextSteps,
}: SectionPlaceholderProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">{title}</h1>
      <p className="mt-3 max-w-3xl text-sm text-slate-600 sm:text-base">{description}</p>
      <div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Planned extension points
        </p>
        <ul className="mt-2 space-y-2 text-sm text-slate-700">
          {nextSteps.map((step) => (
            <li key={step}>- {step}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
