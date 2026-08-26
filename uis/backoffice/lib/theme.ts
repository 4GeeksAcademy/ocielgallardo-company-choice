export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "healthcore-theme";

export function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (value === "light" || value === "dark") {
      return value;
    }
  } catch {
    // ignore storage errors
  }
  return null;
}

export function getPreferredTheme(): Theme {
  const stored = getStoredTheme();
  if (stored) {
    return stored;
  }
  if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") {
    return;
  }
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function setTheme(theme: Theme): void {
  applyTheme(theme);
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // ignore storage errors
  }
}

export function toggleTheme(): Theme {
  const next: Theme = document.documentElement.classList.contains("dark") ? "light" : "dark";
  setTheme(next);
  return next;
}

/** Inline script for root layout — prevents FOUC before hydration. */
export const THEME_INIT_SCRIPT = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var t=localStorage.getItem(k);var d=t==="dark"||(t!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);}catch(e){}})();`;
