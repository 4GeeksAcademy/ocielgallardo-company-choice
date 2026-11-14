"use client";

import { useEffect, useRef, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BackofficeShell } from "@/components/layout/BackofficeShell";
import {
  buildLoginHref,
  isPublicPath,
  safeNextPath,
  type SessionState,
} from "@/lib/auth/session";
import {
  AUTH_CHANGE_EVENT,
  clearAccessToken,
  readSessionState,
} from "@/lib/services/healthcoreClient";
import { track } from "@/lib/services/telemetry";

/** How often an idle tab re-checks the token's `exp`. */
const SESSION_CHECK_INTERVAL_MS = 30_000;

/**
 * Re-read the session when the token changes (this tab or another), when the
 * tab regains focus / becomes visible, and periodically while it stays open.
 */
function subscribeSession(onStoreChange: () => void) {
  if (typeof window === "undefined") {
    return () => {};
  }
  const onVisibility = () => {
    if (document.visibilityState === "visible") onStoreChange();
  };
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(AUTH_CHANGE_EVENT, onStoreChange);
  window.addEventListener("focus", onStoreChange);
  document.addEventListener("visibilitychange", onVisibility);
  const timer = window.setInterval(onStoreChange, SESSION_CHECK_INTERVAL_MS);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(AUTH_CHANGE_EVENT, onStoreChange);
    window.removeEventListener("focus", onStoreChange);
    document.removeEventListener("visibilitychange", onVisibility);
    window.clearInterval(timer);
  };
}

function getServerSessionSnapshot(): SessionState {
  return "none";
}

function subscribeNoop() {
  return () => {};
}

/**
 * `false` during SSR and the hydration render, `true` afterwards. Until then the
 * session snapshot is the server one ("none"), so auth decisions must wait.
 */
function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribeNoop,
    () => true,
    () => false
  );
}

function SessionCheckScreen() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-screen items-center justify-center"
    >
      <span
        aria-hidden="true"
        className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600 dark:border-slate-600 dark:border-t-blue-400"
      />
      <span className="sr-only">Checking your session…</span>
    </div>
  );
}

interface AppChromeProps {
  children: React.ReactNode;
}

/**
 * Client-side auth guard for the whole backoffice (the JWT lives in
 * localStorage, so a server proxy cannot see it). Protected routes render
 * nothing but a spinner until a non-expired token is confirmed; otherwise the
 * user is sent to `/login?next=<route>` (with `reason=expired` when a stale
 * token was found, which is then cleared).
 */
export function AppChrome({ children }: AppChromeProps) {
  const pathname = usePathname();
  const router = useRouter();
  const session = useSyncExternalStore(
    subscribeSession,
    readSessionState,
    getServerSessionSnapshot
  );
  const hydrated = useHydrated();
  const isAuthPage = isPublicPath(pathname);
  const authorized = hydrated && session === "valid";

  const shouldRedirectHome = isAuthPage && authorized;
  const shouldRedirectLogin = hydrated && !isAuthPage && !authorized;

  /* ── page_viewed (only for pages the visitor may actually see) ── */
  const canTrackPage = isAuthPage || authorized;
  const prevPathRef = useRef<string | null>(null);
  useEffect(() => {
    if (!canTrackPage || pathname === prevPathRef.current) return;
    const referrer = prevPathRef.current ?? "";
    prevPathRef.current = pathname;
    track("page_viewed", {
      path: pathname,
      app: "backoffice" as const,
      referrer_path: referrer,
    });
  }, [pathname, canTrackPage]);

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

  /* ── auth redirects ──────────────────────────────────────────── */
  // Route for which a login redirect was already issued, so clearing the stale
  // token (expired → none) does not fire a second redirect without the notice.
  const loginRedirectForRef = useRef<string | null>(null);
  useEffect(() => {
    if (authorized) {
      loginRedirectForRef.current = null;
    }
    if (shouldRedirectHome) {
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(safeNextPath(next));
      return;
    }
    if (shouldRedirectLogin && loginRedirectForRef.current !== pathname) {
      loginRedirectForRef.current = pathname;
      const current = `${pathname}${window.location.search}${window.location.hash}`;
      const expired = session === "expired";
      router.replace(buildLoginHref(current, { expired }));
      if (expired) {
        clearAccessToken();
      }
    }
  }, [authorized, shouldRedirectHome, shouldRedirectLogin, session, pathname, router]);

  if (isAuthPage) {
    return shouldRedirectHome ? <SessionCheckScreen /> : <>{children}</>;
  }

  // Protected route: never paint the shell or the page without a valid token.
  if (!authorized) {
    return <SessionCheckScreen />;
  }

  return <BackofficeShell>{children}</BackofficeShell>;
}
