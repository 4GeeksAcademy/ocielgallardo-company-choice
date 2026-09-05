"use client";

import { useCallback, useState } from "react";
import { AccountMenu } from "@/components/layout/AccountMenu";
import { DesktopSidebar } from "@/components/layout/DesktopSidebar";
import { MobileBottomBar } from "@/components/layout/MobileBottomBar";
import { OfficeMenu } from "@/components/layout/OfficeMenu";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/Button";
import { clearSessionAndRedirectToLogin } from "@/lib/services/healthcoreClient";
import { track } from "@/lib/services/telemetry";

interface BackofficeShellProps {
  children: React.ReactNode;
}

export function BackofficeShell({ children }: BackofficeShellProps) {
  const [officeOpen, setOfficeOpen] = useState(false);
  const closeOffice = useCallback(() => setOfficeOpen(false), []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-50 dark:bg-slate-950 dark:text-slate-100">
      <DesktopSidebar />

      <div className="md:pl-60">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 shadow-[0_4px_14px_rgba(15,23,42,0.07)] backdrop-blur dark:border-slate-700 dark:bg-slate-900/95 dark:shadow-[0_4px_14px_rgba(0,0,0,0.35)]">
          <div className="flex h-20 items-center justify-between gap-4 px-5 sm:px-6">
            <div className="flex items-center gap-3 md:hidden">
              <span
                className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white"
                aria-hidden="true"
              >
                HC
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300 dark:text-blue-400">
                  HealthCore
                </p>
                <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-50 dark:text-slate-100">
                  Internal Backoffice
                </h1>
              </div>
            </div>

            <p className="hidden text-xs text-slate-600 dark:text-slate-300 md:block">
              Clinical Ops · Patient Access · Revenue Cycle
            </p>

            <div className="ml-auto flex items-center gap-2">
              <ThemeToggle />
              <AccountMenu />
              <Button
                type="button"
                variant="primary"
                className="shrink-0 text-xs"
                onClick={() => {
                  track("logout_completed", { path: window.location.pathname });
                  clearSessionAndRedirectToLogin();
                }}
              >
                Cerrar sesión
              </Button>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-5 pb-24 sm:px-6 md:pb-5 lg:px-8">
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
