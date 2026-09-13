"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, LayoutDashboard } from "lucide-react";
import { DASHBOARD_HREF, isPathActive } from "@/components/layout/navConfig";

interface MobileBottomBarProps {
  officeOpen: boolean;
  onOfficeToggle: () => void;
}

export function MobileBottomBar({
  officeOpen,
  onOfficeToggle,
}: MobileBottomBarProps) {
  const pathname = usePathname();
  const dashboardActive = isPathActive(pathname, DASHBOARD_HREF);

  return (
    <nav
      aria-label="Mobile primary"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 shadow-[0_-4px_14px_rgba(15,23,42,0.07)] backdrop-blur dark:border-slate-700 dark:bg-slate-900/95 dark:shadow-[0_-4px_14px_rgba(0,0,0,0.35)] md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="grid h-14 grid-cols-2">
        <Link
          href={DASHBOARD_HREF}
          aria-current={dashboardActive ? "page" : undefined}
          className={`flex flex-col items-center justify-center gap-0.5 text-xs font-medium transition ${
            dashboardActive
              ? "text-blue-700 dark:text-blue-300"
              : "text-slate-700 hover:text-blue-700 dark:text-slate-300 dark:hover:text-blue-300"
          }`}
        >
          <LayoutDashboard size={18} strokeWidth={2} aria-hidden="true" />
          Dashboard
        </Link>
        <button
          type="button"
          className={`flex flex-col items-center justify-center gap-0.5 text-xs font-medium transition ${
            officeOpen
              ? "text-blue-700 dark:text-blue-300"
              : "text-slate-700 hover:text-blue-700 dark:text-slate-300 dark:hover:text-blue-300"
          }`}
          aria-expanded={officeOpen}
          aria-controls="office-menu-panel"
          onClick={onOfficeToggle}
        >
          <Building2 size={18} strokeWidth={2} aria-hidden="true" />
          Office
        </button>
      </div>
    </nav>
  );
}
