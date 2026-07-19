import Link from "next/link";
import { SITE_COPY } from "@/lib/content";
import { HeroCarousel } from "./HeroCarousel";

export function HeroSection() {
  return (
    <section className="hero-grid relative overflow-hidden rounded-2xl border border-slate-200 bg-white px-5 py-10 shadow-sm sm:px-8 sm:py-14">
      <HeroCarousel />
      <div className="relative z-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--brand-600)]">
          HealthCore Public Website
        </p>
        <h1 className="mt-3 max-w-3xl font-serif text-3xl font-bold leading-tight text-slate-900 sm:text-5xl">
          Access-focused outpatient care for patients and clinical teams.
        </h1>
        <p className="mt-5 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
          {SITE_COPY.summary}
        </p>
        <div className="mt-7 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/application"
            className="rounded-md bg-[var(--brand-600)] px-5 py-3 text-center text-sm font-semibold text-white transition hover:bg-[var(--brand-700)]"
          >
            Start application
          </Link>
          <a
            href="#services"
            className="rounded-md border border-slate-300 bg-white px-5 py-3 text-center text-sm font-semibold text-slate-700 transition hover:border-slate-400"
          >
            Explore services
          </a>
        </div>
      </div>
    </section>
  );
}
