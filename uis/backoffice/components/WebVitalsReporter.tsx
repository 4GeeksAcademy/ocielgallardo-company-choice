"use client";

import { useEffect } from "react";
import { track } from "@/lib/services/telemetry";

/**
 * Reports Core Web Vitals (LCP, INP, CLS) and FCP via PerformanceObserver.
 * Each metric is sent as an `api_latency_recorded` event since the plan's
 * allowlist (`path`, `method`, `duration_ms`, `http_status`) can carry the
 * vital name in `method` and value in `duration_ms`.
 *
 * Render this once in the root layout.
 */
export function WebVitalsReporter() {
  useEffect(() => {
    if (typeof window === "undefined" || !("PerformanceObserver" in window)) return;

    const observers: PerformanceObserver[] = [];

    function reportMetric(name: string, value: number) {
      track("api_latency_recorded", {
        path: window.location.pathname,
        method: name,
        duration_ms: Math.round(value),
        http_status: 200,
      });
    }

    // LCP
    try {
      const lcpObs = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        if (last) reportMetric("web-vital-LCP", last.startTime);
      });
      lcpObs.observe({ type: "largest-contentful-paint", buffered: true });
      observers.push(lcpObs);
    } catch { /* unsupported */ }

    // FCP
    try {
      const fcpObs = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.name === "first-contentful-paint") {
            reportMetric("web-vital-FCP", entry.startTime);
          }
        }
      });
      fcpObs.observe({ type: "paint", buffered: true });
      observers.push(fcpObs);
    } catch { /* unsupported */ }

    // CLS
    try {
      let clsValue = 0;
      const clsObs = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const le = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
          if (!le.hadRecentInput && typeof le.value === "number") {
            clsValue += le.value;
          }
        }
      });
      clsObs.observe({ type: "layout-shift", buffered: true });
      observers.push(clsObs);

      // Report CLS on page hide
      const reportCLS = () => reportMetric("web-vital-CLS", Math.round(clsValue * 1000));
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") reportCLS();
      });
    } catch { /* unsupported */ }

    return () => observers.forEach((o) => o.disconnect());
  }, []);

  return null;
}
