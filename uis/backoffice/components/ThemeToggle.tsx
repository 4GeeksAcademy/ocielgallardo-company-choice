"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import {
  applyTheme,
  getPreferredTheme,
  toggleTheme,
  type Theme,
} from "@/lib/theme";

interface ThemeToggleProps {
  className?: string;
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
      className={`inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-blue-400 dark:hover:bg-slate-700 dark:hover:text-blue-300 dark:focus-visible:ring-offset-slate-900 ${className}`}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Light mode" : "Dark mode"}
      onClick={() => setThemeState(toggleTheme())}
    >
      {mounted ? (
        theme === "dark" ? (
          <Sun size={20} strokeWidth={2} aria-hidden="true" />
        ) : (
          <Moon size={20} strokeWidth={2} aria-hidden="true" />
        )
      ) : (
        <Moon size={20} strokeWidth={2} aria-hidden="true" />
      )}
    </button>
  );
}
