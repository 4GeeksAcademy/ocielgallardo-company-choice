import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { WORK_NAV_GROUPS, type NavGroup } from "@/components/layout/navConfig";

/** Groups intentionally left off the dashboard grid (still reachable from the sidebar). */
const HIDDEN_ON_DASHBOARD = new Set(["people-talent"]);

function moduleHref(group: NavGroup): string {
  return group.href ?? group.items[0]?.href ?? "/";
}

/** Module shortcuts generated from the sidebar config, so both stay in sync. */
export function ModuleGrid() {
  const modules = WORK_NAV_GROUPS.filter((group) => !HIDDEN_ON_DASHBOARD.has(group.id));
  return (
    <section aria-labelledby="dashboard-modules-heading">
      <h2 id="dashboard-modules-heading" className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-50">
        Modules
      </h2>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {modules.map((group) => (
          <li key={group.id}>
            <Link
              href={moduleHref(group)}
              className="group flex h-full items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-500"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-primary dark:bg-blue-950/50">
                <group.icon size={18} strokeWidth={2} aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50">{group.label}</h3>
                {group.description ? (
                  <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-300">{group.description}</p>
                ) : null}
              </div>
              <ArrowRight
                size={14}
                aria-hidden="true"
                className="mt-1 shrink-0 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-primary"
              />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
