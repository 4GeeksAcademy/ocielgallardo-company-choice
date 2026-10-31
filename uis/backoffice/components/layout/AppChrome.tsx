"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BackofficeShell } from "@/components/layout/BackofficeShell";
import { getAccessToken } from "@/lib/services/healthcoreClient";
import { track } from "@/lib/services/telemetry";

const AUTH_PATHS = new Set(["/login", "/register", "/forgot-password", "/reset-password"]);

function subscribe(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }
  window.addEventListener("storage", onStoreChange);
  return () => window.removeEventListener("storage", onStoreChange);
}

function getTokenSnapshot(): string | null {
  return getAccessToken();
}

function getServerTokenSnapshot(): string | null {
  return null;
}

function subscribeNoop() {
  return () => {};
}

/**
 * `false` during SSR and the hydration render, `true` afterwards. Until then the
 * token snapshot is the server one (`null`), so auth redirects must wait for it.
 */
function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribeNoop,
    () => true,
    () => false
  );
}

interface AppChromeProps {
  children: React.ReactNode;
}

export function AppChrome({ children }: AppChromeProps) {
  const pathname = usePathname();
  const router = useRouter();
  const token = useSyncExternalStore(
    subscribe,
    getTokenSnapshot,
    getServerTokenSnapshot
  );
  const hydrated = useHydrated();
  const isAuthPage = AUTH_PATHS.has(pathname);

  const shouldRedirectHome = hydrated && isAuthPage && Boolean(token);
  const shouldRedirectLogin = hydrated && !isAuthPage && !token;

  /* ── page_viewed ─────────────────────────────────────────────── */
  const prevPathRef = useRef<string | null>(null);
  useEffect(() => {
    if (pathname === prevPathRef.current) return;
    const referrer = prevPathRef.current ?? "";
    prevPathRef.current = pathname;
    track("page_viewed", {
      path: pathname,
      app: "backoffice" as const,
      referrer_path: referrer,
    });
  }, [pathname]);

  /* ── frontend_error_captured (global) ────────────────────────── */
  useEffect(() => {
    function onError(event: ErrorEvent) {
      track("frontend_error_captured", {
        path: window.location.pathname,
        error_name: event.error?.name ?? "Error",
        component: "window",
      });
    }
    function onRejection(event: PromiseRejectionEvent) {
      const name =
        event.reason instanceof Error ? event.reason.name : "UnhandledRejection";
      track("frontend_error_captured", {
        path: window.location.pathname,
        error_name: name,
        component: "promise",
      });
    }
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);

  useEffect(() => {
    if (shouldRedirectHome) {
      router.replace("/");
      return;
    }
    if (shouldRedirectLogin) {
      router.replace("/login");
    }
  }, [shouldRedirectHome, shouldRedirectLogin, router]);

  const awaitingSession = !hydrated && !isAuthPage;
  if (awaitingSession || shouldRedirectHome || shouldRedirectLogin) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex min-h-screen items-center justify-center text-sm text-slate-500 dark:text-slate-400"
      >
        Loading…
      </div>
    );
  }

  if (isAuthPage) {
    return <>{children}</>;
  }

  return <BackofficeShell>{children}</BackofficeShell>;
}
