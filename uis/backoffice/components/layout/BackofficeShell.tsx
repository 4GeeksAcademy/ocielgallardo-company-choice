import Link from "next/link";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/patients", label: "Patients" },
  { href: "/appointments", label: "Appointments" },
  { href: "/billing", label: "Billing" },
  { href: "/claims", label: "Claims" },
  { href: "/reports", label: "Reports" },
  { href: "/applications", label: "People & Talent" },
] as const;

interface BackofficeShellProps {
  children: React.ReactNode;
}

export function BackofficeShell({ children }: BackofficeShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span
                className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white"
                aria-hidden="true"
              >
                HC
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                  HealthCore
                </p>
                <h1 className="text-sm font-semibold text-slate-900 sm:text-base">
                  Internal Backoffice
                </h1>
              </div>
            </div>
            <p className="hidden text-xs text-slate-500 sm:block">
              Clinical Ops · Patient Access · Revenue Cycle
            </p>
          </div>

          <nav aria-label="Backoffice sections" className="flex flex-wrap gap-2">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-blue-200 hover:text-blue-700"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}
