"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  WORK_NAV_GROUPS,
  isGroupActive,
  isPathActive,
  linkClassName,
  type NavGroup,
} from "@/components/layout/navConfig";

interface OfficeMenuProps {
  open: boolean;
  onClose: () => void;
}

function OfficeGroup({
  group,
  onNavigate,
}: {
  group: NavGroup;
  onNavigate: () => void;
}) {
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
        className={`block rounded-md px-3 py-2.5 text-sm transition ${linkClassName(active)}`}
        onClick={onNavigate}
      >
        {group.label}
      </Link>
    );
  }

  return (
    <div>
      <button
        type="button"
        className={`flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left text-sm font-medium transition ${
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
                  className={`block rounded-md px-2.5 py-2 text-sm transition ${linkClassName(active)}`}
                  onClick={onNavigate}
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

export function OfficeMenu({ open, onClose }: OfficeMenuProps) {
  const pathname = usePathname();
  const previousPathname = useRef(pathname);

  useEffect(() => {
    if (previousPathname.current !== pathname) {
      previousPathname.current = pathname;
      onClose();
    }
  }, [pathname, onClose]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 md:hidden" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/30"
        aria-label="Close Office menu"
        onClick={onClose}
      />
      <div
        id="office-menu-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Office modules"
        className="absolute inset-x-0 bottom-14 max-h-[70vh] overflow-y-auto rounded-t-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
        style={{ marginBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="sticky top-0 border-b border-slate-100 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 dark:text-slate-300">
            Office
          </p>
        </div>
        <nav className="space-y-1 px-3 py-3">
          {WORK_NAV_GROUPS.map((group) => (
            <OfficeGroup key={group.id} group={group} onNavigate={onClose} />
          ))}
        </nav>
      </div>
    </div>
  );
}
