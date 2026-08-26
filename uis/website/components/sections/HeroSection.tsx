import Link from "next/link";
import { SITE_COPY } from "@/lib/content";
import { HeroCarousel } from "./HeroCarousel";

export function HeroSection() {
  return (
    <section className="hero-grid relative overflow-hidden rounded-2xl border border-slate-200 bg-white px-5 py-10 shadow-sm dark:border-slate-700 dark:bg-slate-900/90 sm:px-8 sm:py-14">
      <HeroCarousel />
      <div className="relative z-10">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-(--brand-fg)">
          HealthCore Public Website
        </p>
        <h1 className="mt-3 max-w-3xl font-serif text-3xl font-extrabold leading-tight text-slate-950 dark:text-white sm:text-5xl">
          Access-focused outpatient care for patients and clinical teams.
        </h1>
        <p className="mt-5 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-200 sm:text-base">
          {SITE_COPY.summary}
        </p>
        <div className="mt-7 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/application"
            className="rounded-lg bg-(--brand-600) px-5 py-3 text-center text-sm font-semibold text-white transition hover:bg-(--brand-700)"
          >
            Start application
          </Link>
          <a
            href="#services"
            className="rounded-lg border border-slate-300 bg-white/90 px-5 py-3 text-center text-sm font-semibold text-slate-800 transition hover:border-slate-400 dark:border-slate-500 dark:bg-slate-900/80 dark:text-slate-100 dark:hover:border-slate-400"
          >
            Explore services
          </a>
        </div>
      </div>
    </section>
  );
}
