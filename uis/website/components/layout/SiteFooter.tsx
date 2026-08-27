export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-slate-800 bg-slate-950 text-slate-100">
      <div className="mx-auto grid w-full max-w-6xl gap-4 px-4 py-8 sm:grid-cols-2 sm:px-6 lg:px-8">
        <div>
          <p className="text-sm font-semibold text-white">HealthCore</p>
          <p className="mt-2 text-sm text-slate-300">
            Outpatient network modernization across the US and UK.
          </p>
        </div>
        <div className="sm:text-right">
          <p className="text-xs uppercase tracking-wide text-slate-400">Compliance context</p>
          <p className="mt-2 text-sm text-slate-200">HIPAA (US) and UK GDPR (UK)</p>
        </div>
      </div>
    </footer>
  );
}
