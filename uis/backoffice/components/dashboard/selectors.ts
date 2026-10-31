/**
 * Pure, presentation-only aggregations for the home dashboard.
 * They only reshape responses from the existing API clients; no business rules live here.
 */
import type { IncidentSummary } from "@/types/incidentManager";
import { stockLevelFor, type InventoryOrder, type MedicalSupply } from "@/types/inventory";
import type { MonthlyClinicSupplyPerformance } from "@/types/reporting";
import type { Supplier } from "@/types/suppliers";
import type { TelemetryReport } from "@/types/telemetry";
import type { RfpTicketSummary } from "@/lib/services/rfpApi";

const DAY_MS = 24 * 60 * 60 * 1000;

/** "austin_north" → "Austin North" */
export function humanizeKey(key: string): string {
  return key
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function utcDayKey(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function shortDayLabel(dayKey: string): string {
  return new Date(`${dayKey}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}

/* ── Incidents ─────────────────────────────────────────── */

export interface IncidentStatusView {
  open: number;
  inProgress: number;
  resolved: number;
  discarded: number;
  active: number;
  total: number;
}

export function toIncidentStatusView(summary: IncidentSummary): IncidentStatusView {
  const by = summary.by_status ?? {};
  const open = by.open ?? 0;
  const inProgress = by.in_progress ?? 0;
  return {
    open,
    inProgress,
    resolved: by.resolved ?? 0,
    discarded: by.discarded ?? 0,
    active: open + inProgress,
    total: summary.total ?? 0,
  };
}

export interface LabelValue {
  label: string;
  value: number;
}

/** Top-N entries of a count map, the rest folded into "Other". */
export function topEntries(counts: Record<string, number>, limit = 6): LabelValue[] {
  const sorted = Object.entries(counts ?? {})
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1]);
  const top = sorted.slice(0, limit).map(([key, value]) => ({ label: humanizeKey(key), value }));
  const rest = sorted.slice(limit).reduce((sum, [, value]) => sum + value, 0);
  return rest > 0 ? [...top, { label: "Other", value: rest }] : top;
}

/* ── RFP intake ────────────────────────────────────────── */

export const RFP_AWAITING_STATUSES = ["waiting_for_approval", "needs_human_review"] as const;

export interface RfpView {
  awaiting: number;
  waitingForApproval: number;
  needsReview: number;
  receivedInWindow: number;
  /** Tickets created per week, oldest first. */
  weekly: number[];
}

export function toRfpView(tickets: RfpTicketSummary[], now: Date, weeks = 8): RfpView {
  const waitingForApproval = tickets.filter((t) => t.status === "waiting_for_approval").length;
  const needsReview = tickets.filter((t) => t.status === "needs_human_review").length;
  const weekly = new Array<number>(weeks).fill(0);
  const windowStart = now.getTime() - weeks * 7 * DAY_MS;
  for (const ticket of tickets) {
    const created = Date.parse(ticket.created_at);
    if (Number.isNaN(created) || created < windowStart || created > now.getTime()) continue;
    const index = Math.min(weeks - 1, Math.floor((created - windowStart) / (7 * DAY_MS)));
    weekly[index] += 1;
  }
  return {
    awaiting: waitingForApproval + needsReview,
    waitingForApproval,
    needsReview,
    receivedInWindow: weekly.reduce((sum, value) => sum + value, 0),
    weekly,
  };
}

/* ── Inventory ─────────────────────────────────────────── */

export interface StockView {
  critical: number;
  low: number;
  healthy: number;
  total: number;
}

export function toStockView(supplies: MedicalSupply[]): StockView {
  const view: StockView = { critical: 0, low: 0, healthy: 0, total: supplies.length };
  for (const supply of supplies) {
    view[stockLevelFor(supply.current_stock)] += 1;
  }
  return view;
}

export interface MovementDay {
  day: string;
  label: string;
  inbound: number;
  outbound: number;
}

/** Number of inbound / outbound orders per UTC day over the last `days` days (oldest first). */
export function toMovementDays(orders: InventoryOrder[], now: Date, days = 14): MovementDay[] {
  const buckets = new Map<string, MovementDay>();
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const key = utcDayKey(new Date(now.getTime() - offset * DAY_MS));
    buckets.set(key, { day: key, label: shortDayLabel(key), inbound: 0, outbound: 0 });
  }
  for (const order of orders) {
    const bucket = buckets.get((order.created_at ?? "").slice(0, 10));
    if (!bucket) continue;
    if (order.order_type === "inbound") bucket.inbound += 1;
    else if (order.order_type === "outbound") bucket.outbound += 1;
  }
  return [...buckets.values()];
}

/* ── Telemetry ─────────────────────────────────────────── */

export interface PlatformHealthView {
  totalEvents: number;
  eventsPerDay: number[];
  avgLatencyMs: number | null;
  authFailureRate: number | null;
  authAttempts: number;
}

export function toPlatformHealthView(report: TelemetryReport): PlatformHealthView {
  const metrics = report.metrics;
  const days = [...(metrics.events_per_day ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const latencySamples = (metrics.avg_latency_by_path ?? []).reduce((sum, row) => sum + row.sample_count, 0);
  const latencyWeighted = (metrics.avg_latency_by_path ?? []).reduce(
    (sum, row) => sum + row.avg_duration_ms * row.sample_count,
    0,
  );
  const authRows = metrics.auth_failure_rate ?? [];
  const authAttempts = authRows.reduce((sum, row) => sum + row.total_attempts, 0);
  const authFailed = authRows.reduce((sum, row) => sum + row.failed, 0);
  return {
    totalEvents: days.reduce((sum, row) => sum + row.count, 0),
    eventsPerDay: days.map((row) => row.count),
    avgLatencyMs: latencySamples > 0 ? latencyWeighted / latencySamples : null,
    authFailureRate: authAttempts > 0 ? authFailed / authAttempts : null,
    authAttempts,
  };
}

/* ── Reporting ─────────────────────────────────────────── */

export interface ClinicSupplyView {
  monthStart: string | null;
  stockoutsByClinic: LabelValue[];
  totalStockouts: number;
  totalExpiryRisk: number;
  clinicCount: number;
}

export function toClinicSupplyView(report: MonthlyClinicSupplyPerformance): ClinicSupplyView {
  const clinics = report.clinics ?? [];
  return {
    monthStart: report.month_start,
    stockoutsByClinic: clinics
      .map((clinic) => ({ label: `Clinic ${clinic.clinic_id} (${clinic.country})`, value: clinic.critical_stockout_count }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6),
    totalStockouts: clinics.reduce((sum, clinic) => sum + clinic.critical_stockout_count, 0),
    totalExpiryRisk: clinics.reduce((sum, clinic) => sum + clinic.expiry_risk_count, 0),
    clinicCount: clinics.length,
  };
}

/* ── Suppliers ─────────────────────────────────────────── */

export interface SupplierRenewal {
  id: number;
  name: string;
  date: string;
  daysLeft: number;
}

export interface SupplierView {
  active: number;
  suspended: number;
  renewals: SupplierRenewal[];
}

export function toSupplierView(suppliers: Supplier[], now: Date, windowDays = 60): SupplierView {
  const renewals: SupplierRenewal[] = [];
  for (const supplier of suppliers) {
    if (!supplier.contract_renewal_date) continue;
    const due = Date.parse(supplier.contract_renewal_date);
    if (Number.isNaN(due)) continue;
    const daysLeft = Math.ceil((due - now.getTime()) / DAY_MS);
    if (daysLeft >= 0 && daysLeft <= windowDays) {
      renewals.push({ id: supplier.id, name: supplier.name, date: supplier.contract_renewal_date, daysLeft });
    }
  }
  renewals.sort((a, b) => a.daysLeft - b.daysLeft);
  return {
    active: suppliers.filter((s) => s.status === "active").length,
    suspended: suppliers.filter((s) => s.status === "suspended").length,
    renewals,
  };
}
