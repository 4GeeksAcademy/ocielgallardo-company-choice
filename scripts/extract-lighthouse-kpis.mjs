#!/usr/bin/env node
/**
 * Extract Core Web Vitals and Performance score from Lighthouse HTML exports.
 * Parses window.__LIGHTHOUSE_JSON__ embedded in DevTools / Lighthouse reports.
 *
 * Usage:
 *   node scripts/extract-lighthouse-kpis.mjs docs/audit/before/*.html
 *   node scripts/extract-lighthouse-kpis.mjs docs/audit/after/*.html --markdown
 */

import { readFileSync } from "node:fs";
import { basename } from "node:path";

const MARKER = "window.__LIGHTHOUSE_JSON__ = ";

function parseLighthouseHtml(filePath) {
  const html = readFileSync(filePath, "utf8");
  const start = html.indexOf(MARKER);
  if (start < 0) {
    throw new Error(`${filePath}: missing ${MARKER}`);
  }
  const jsonStart = start + MARKER.length;
  const jsonEnd = html.indexOf(";</script>", jsonStart);
  if (jsonEnd < 0) {
    throw new Error(`${filePath}: could not find end of Lighthouse JSON`);
  }
  return JSON.parse(html.slice(jsonStart, jsonEnd));
}

function auditValue(audits, id) {
  const audit = audits[id];
  if (!audit) return null;
  if (audit.displayValue != null && audit.displayValue !== "") {
    return audit.displayValue;
  }
  if (typeof audit.numericValue === "number") {
    return formatMs(audit.numericValue);
  }
  return null;
}

function formatMs(value) {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)} s`;
  }
  return `${Math.round(value)} ms`;
}

function extractMetrics(report) {
  const { audits, categories } = report;
  const metrics = audits.metrics?.details?.items?.[0] ?? {};

  const perfScore =
    categories?.performance?.score != null
      ? Math.round(categories.performance.score * 100)
      : null;

  const lcp =
    auditValue(audits, "largest-contentful-paint") ??
    (metrics.largestContentfulPaint != null
      ? formatMs(metrics.largestContentfulPaint)
      : null);

  const inp =
    auditValue(audits, "interaction-to-next-paint") ??
    auditValue(audits, "experimental-interaction-to-next-paint") ??
    auditValue(audits, "max-potential-fid") ??
    (metrics.maxPotentialFID != null ? formatMs(metrics.maxPotentialFID) : null);

  const inpNote =
    audits["interaction-to-next-paint"]?.displayValue != null
      ? "INP"
      : "maxPotentialFID (lab proxy)";

  const cls =
    auditValue(audits, "cumulative-layout-shift") ??
    (metrics.cumulativeLayoutShift != null
      ? String(metrics.cumulativeLayoutShift)
      : null);

  const ttfb =
    auditValue(audits, "server-response-time") ??
    (metrics.timeToFirstByte != null ? formatMs(metrics.timeToFirstByte) : null);

  const tbt =
    auditValue(audits, "total-blocking-time") ??
    (metrics.totalBlockingTime != null ? formatMs(metrics.totalBlockingTime) : null);

  const fcp =
    auditValue(audits, "first-contentful-paint") ??
    (metrics.firstContentfulPaint != null
      ? formatMs(metrics.firstContentfulPaint)
      : null);

  return {
    file: basename(report.requestedUrl ?? ""),
    url: report.requestedUrl ?? "",
    fetchTime: report.fetchTime ?? "",
    lighthouseVersion: report.lighthouseVersion ?? "",
    perfScore,
    fcp,
    lcp,
    inp,
    inpNote,
    cls,
    ttfb,
    tbt,
  };
}

function inferLabel(filePath) {
  const name = basename(filePath).toLowerCase();
  const isDesktop = name.includes("desktop");

  if (name.includes("website")) {
    return isDesktop ? "Website `/` Desktop" : "Website `/` Mobile";
  }

  const isLogin =
    name.includes("login") ||
    name === "backoffice-mobile-test.html" ||
    name === "backoffice-desktop-test.html" && filePath.replace(/\\/g, "/").includes("/before/");

  if (isLogin) {
    return isDesktop ? "Backoffice `/login` Desktop" : "Backoffice `/login` Mobile";
  }

  if (name.includes("backoffice") || name.includes("insite")) {
    return isDesktop ? "Backoffice `/` Desktop" : "Backoffice `/` Mobile";
  }

  return basename(filePath);
}

function toMarkdownRow(filePath, row) {
  const surface = inferLabel(filePath);
  return `| ${surface} | ${row.perfScore ?? "—"} | ${row.fcp ?? "—"} | ${row.lcp ?? "—"} | ${row.inp ?? "—"} | ${row.cls ?? "—"} | ${row.ttfb ?? "—"} | ${row.tbt ?? "—"} | \`${basename(filePath)}\` |`;
}

const args = process.argv.slice(2).filter((a) => a !== "--markdown" && a !== "--json");
const markdown = process.argv.includes("--markdown");
const asJson = process.argv.includes("--json");

if (args.length === 0) {
  console.error("Usage: node scripts/extract-lighthouse-kpis.mjs <file.html> [...] [--markdown|--json]");
  process.exit(1);
}

const rows = args.map((filePath) => {
  const report = parseLighthouseHtml(filePath);
  const metrics = extractMetrics(report);
  return { filePath, ...metrics };
});

if (asJson) {
  console.log(JSON.stringify(rows, null, 2));
} else if (markdown) {
  console.log("| Surface | Perf | FCP | LCP | INP* | CLS | TTFB | TBT | File |");
  console.log("|---------|-----:|-----|-----|------|----:|------|-----|------|");
  for (const row of rows) {
    console.log(toMarkdownRow(row.filePath, row));
  }
  console.log("");
  console.log("* INP: `interaction-to-next-paint` when present; otherwise maxPotentialFID (lab proxy).");
} else {
  for (const row of rows) {
    console.log(`${basename(row.filePath)}`);
    console.log(`  url:      ${row.url}`);
    console.log(`  perf:     ${row.perfScore ?? "—"}`);
    console.log(`  FCP:      ${row.fcp ?? "—"}`);
    console.log(`  LCP:      ${row.lcp ?? "—"}`);
    console.log(`  INP*:     ${row.inp ?? "—"} (${row.inpNote})`);
    console.log(`  CLS:      ${row.cls ?? "—"}`);
    console.log(`  TTFB:     ${row.ttfb ?? "—"}`);
    console.log(`  TBT:      ${row.tbt ?? "—"}`);
    console.log("");
  }
}
