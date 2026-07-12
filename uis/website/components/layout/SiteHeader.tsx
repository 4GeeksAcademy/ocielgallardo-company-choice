import Link from "next/link";
import { SITE_COPY } from "@/lib/content";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--brand-600)] text-sm font-bold text-white"
            aria-hidden="true"
          >
            HC
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-900">{SITE_COPY.brand}</p>
            <p className="text-xs text-slate-600">{SITE_COPY.tagline}</p>
          </div>
        </div>

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
