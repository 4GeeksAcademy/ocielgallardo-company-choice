"use client";

import { useCallback, useState } from "react";
import { usePathname } from "next/navigation";
import { AccountMenu } from "@/components/layout/AccountMenu";
import { DesktopSidebar } from "@/components/layout/DesktopSidebar";
import { MobileBottomBar } from "@/components/layout/MobileBottomBar";
import { OfficeMenu } from "@/components/layout/OfficeMenu";
import { getSectionLabel } from "@/components/layout/navConfig";
import { ThemeToggle } from "@/components/ThemeToggle";

interface BackofficeShellProps {
  children: React.ReactNode;
}

export function BackofficeShell({ children }: BackofficeShellProps) {
  const pathname = usePathname();
  const sectionLabel = getSectionLabel(pathname);
  const [officeOpen, setOfficeOpen] = useState(false);
  const closeOffice = useCallback(() => setOfficeOpen(false), []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-700 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-700"
      >
        Skip to main content
      </a>
      <DesktopSidebar />

      <div className="md:pl-60">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
          <div className="flex h-14 items-center justify-between gap-4 px-4 sm:px-6 md:h-16">
            <div className="flex min-w-0 items-center gap-3">
              <span
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white md:hidden"
                aria-hidden="true"
              >
                HC
              </span>
              <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100 md:text-base">
                <span className="sr-only">HealthCore Backoffice · </span>
                {sectionLabel}
              </p>
            </div>

            <div className="ml-auto flex items-center gap-2">
              <ThemeToggle />
              <AccountMenu />
            </div>
          </div>
        </header>

        <main
          id="main-content"
          tabIndex={-1}
          className="mx-auto w-full max-w-7xl focus:outline-none px-4 py-5 pb-24 sm:px-6 md:pb-5 lg:px-8">
          {children}
        </main>
      </div>

      <MobileBottomBar
        officeOpen={officeOpen}
        onOfficeToggle={() => setOfficeOpen((value) => !value)}
      />
      <OfficeMenu open={officeOpen} onClose={closeOffice} />
    </div>
  );
}
