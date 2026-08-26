"use client";

import { useEffect, useState } from "react";
import {
  applyTheme,
  getPreferredTheme,
  toggleTheme,
  type Theme,
} from "@/lib/theme";

interface ThemeToggleProps {
  className?: string;
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
      <circle cx="12" cy="12" r="3.5" />
      <path strokeLinecap="round" d="M12 3v1.5M12 19.5V21M3 12h1.5M19.5 12H21M5.6 5.6l1.1 1.1M17.3 17.3l1.1 1.1M5.6 18.4l1.1-1.1M17.3 6.7l1.1-1.1" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20.5 14.2A7.5 7.5 0 0 1 9.8 3.5 7.8 7.8 0 1 0 20.5 14.2z"
      />
    </svg>
  );
}

export function ThemeToggle({ className = "" }: ThemeToggleProps) {
  const [theme, setThemeState] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const preferred = getPreferredTheme();
    applyTheme(preferred);
    setThemeState(preferred);
    setMounted(true);
  }, []);

  return (
    <button
      type="button"
      className={`inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 hover:text-[var(--brand-fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-600)] dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 dark:hover:text-[var(--brand-fg)] ${className}`}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Light mode" : "Dark mode"}
      onClick={() => setThemeState(toggleTheme())}
    >
      {mounted ? (theme === "dark" ? <SunIcon /> : <MoonIcon />) : <MoonIcon />}
    </button>
  );
}
