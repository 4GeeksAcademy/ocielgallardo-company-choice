import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 overflow-visible border-b border-slate-200/70 bg-white/90 backdrop-blur">
      {/* Altura bloqueada: el logo crece sin empujar el navbar */}
      <div className="mx-auto flex h-16 min-h-16 max-h-16 w-full max-w-6xl items-center justify-between overflow-visible px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex shrink-0 items-center overflow-visible">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/icons/logo-02.png"
            alt="HealthCore"
            className="h-[3.375rem] w-auto sm:h-[3.75rem]"
          />
        </Link>

        <nav className="flex items-center gap-2 text-sm">
          <a href="#services" className="rounded-md px-3 py-2 font-medium text-slate-700 hover:bg-slate-100">
            Services
          </a>
          <a href="#impact" className="rounded-md px-3 py-2 font-medium text-slate-700 hover:bg-slate-100">
            Impact
          </a>
          <Link
            href="/application"
            className="rounded-md bg-[var(--brand-600)] px-3 py-2 font-semibold text-white transition hover:bg-[var(--brand-700)]"
          >
            Apply now
          </Link>
        </nav>
      </div>
    </header>
  );
}
