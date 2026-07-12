export function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white"
            aria-hidden="true"
          >
            HC
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-blue-600">
              HealthCore
            </p>
            <h1 className="text-sm font-semibold text-slate-900 sm:text-base">
              People &amp; Talent · Pipeline de candidaturas
            </h1>
          </div>
        </div>
        <p className="hidden text-xs text-slate-500 sm:block">
          Diane Foster · Personas y Fuerza Laboral
        </p>
      </div>
    </header>
  );
}
