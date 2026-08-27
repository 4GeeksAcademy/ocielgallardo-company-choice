"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  DASHBOARD_HREF,
  WORK_NAV_GROUPS,
  isGroupActive,
  isPathActive,
  linkClassName,
  type NavGroup,
} from "@/components/layout/navConfig";

function NavGroupSection({ group }: { group: NavGroup }) {
  const pathname = usePathname();
  const groupActive = isGroupActive(pathname, group);
  const hasChildren = group.items.length > 0;
  const [expanded, setExpanded] = useState(groupActive);

  useEffect(() => {
    if (groupActive) {
      setExpanded(true);
    }
  }, [groupActive]);

  if (!hasChildren && group.href) {
    const active = isPathActive(pathname, group.href);
    return (
      <Link
        href={group.href}
        aria-current={active ? "page" : undefined}
        className={`block rounded-md px-3 py-2 text-sm transition ${linkClassName(active)}`}
      >
        {group.label}
      </Link>
    );
  }

  return (
    <div>
      <button
        type="button"
        className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-medium transition ${
          groupActive
            ? "text-blue-700 dark:text-blue-300"
            : "text-slate-800 dark:text-slate-100 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
        }`}
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <span>{group.label}</span>
        <span className="text-xs text-slate-400" aria-hidden="true">
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {expanded ? (
        <ul className="mt-1 space-y-0.5 border-l border-slate-200 ml-3 pl-2 dark:border-slate-700">
          {group.items.map((item) => {
            const active = isPathActive(pathname, item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`block rounded-md px-2.5 py-1.5 text-sm transition ${linkClassName(active)}`}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

export function DesktopSidebar() {
  const pathname = usePathname();
  const dashboardActive = isPathActive(pathname, DASHBOARD_HREF);

  return (
    <aside
      className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-slate-200 bg-white shadow-[4px_0_16px_rgba(15,23,42,0.08)] dark:border-slate-700 dark:bg-slate-900 dark:shadow-[4px_0_16px_rgba(0,0,0,0.35)] md:flex"
      aria-label="Backoffice navigation"
    >
      <div className="flex h-20 shrink-0 items-center gap-3 border-b border-slate-200 px-5 dark:border-slate-700">
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
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-50 dark:text-slate-100">Backoffice</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <Link
          href={DASHBOARD_HREF}
          aria-current={dashboardActive ? "page" : undefined}
          className={`mb-2 block rounded-md px-3 py-2 text-sm transition ${linkClassName(dashboardActive)}`}
        >
          Dashboard
        </Link>

        {WORK_NAV_GROUPS.map((group) => (
          <NavGroupSection key={group.id} group={group} />
        ))}
      </nav>
    </aside>
  );
}
