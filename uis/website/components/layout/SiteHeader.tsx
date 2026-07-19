"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();

  useEffect(() => {
    if (!menuOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/90 backdrop-blur">
      <div className="relative mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-5 sm:py-4 lg:px-5">
        <Link href="/" className="flex max-w-[min(100%,18rem)] items-center gap-2 sm:gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/icons/logo-01.png"
            alt="HealthCore"
            className="h-10 w-10 shrink-0 object-contain sm:h-12 sm:w-12"
          />
          <span className="hidden min-w-0 sm:block">
            <span className="block text-sm font-semibold leading-tight text-[var(--brand-600)]">
              HealthCore
            </span>
            <span className="mt-0.5 block text-xs leading-snug text-[var(--brand-600)]">
              Smart, secure, and human healthcare
            </span>
          </span>
        </Link>

        <nav className="hidden shrink-0 items-center gap-1 text-sm sm:flex sm:gap-2">
          <a href="#services" className="rounded-md px-2 py-2 font-medium text-slate-700 hover:bg-slate-100 sm:px-3">
            Services
          </a>
          <a href="#impact" className="rounded-md px-2 py-2 font-medium text-slate-700 hover:bg-slate-100 sm:px-3">
            Impact
          </a>
          <Link
            href="/application"
            className="rounded-md bg-[var(--brand-600)] px-2 py-2 font-semibold text-white transition hover:bg-[var(--brand-700)] sm:px-3"
          >
            Apply now
          </Link>
        </nav>

        <div className="sm:hidden">
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md text-[var(--brand-600)] hover:bg-slate-100"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? (
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
              </svg>
            ) : (
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            )}
          </button>

          {menuOpen ? (
            <button
              type="button"
              aria-label="Close menu overlay"
              className="fixed inset-0 z-30 bg-black/40 transition-opacity duration-150"
              onClick={closeMenu}
            />
          ) : null}

          <nav
            id={menuId}
            aria-hidden={!menuOpen}
            className={`absolute right-4 top-full z-40 mt-2 w-48 origin-top-right rounded-xl border border-slate-200 bg-white p-2 shadow-md transition duration-150 ease-out ${
              menuOpen
                ? "pointer-events-auto translate-y-0 scale-100 opacity-100"
                : "pointer-events-none -translate-y-1 scale-95 opacity-0"
            }`}
          >
            <ul className="flex flex-col gap-1 text-sm">
              <li>
                <a
                  href="#services"
                  className="block rounded-md px-3 py-2 font-medium text-[var(--brand-600)] hover:bg-slate-50"
                  onClick={closeMenu}
                >
                  Services
                </a>
              </li>
              <li>
                <a
                  href="#impact"
                  className="block rounded-md px-3 py-2 font-medium text-[var(--brand-600)] hover:bg-slate-50"
                  onClick={closeMenu}
                >
                  Impact
                </a>
              </li>
              <li>
                <Link
                  href="/application"
                  className="block rounded-md px-3 py-2 font-bold text-[var(--brand-600)] hover:bg-slate-50"
                  onClick={closeMenu}
                >
                  Apply now
                </Link>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </header>
  );
}
