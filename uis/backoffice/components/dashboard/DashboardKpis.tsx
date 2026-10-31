"use client";

import { Donut } from "@/components/dashboard/charts/Donut";
import { Sparkline } from "@/components/dashboard/charts/Sparkline";
import { StackedBar } from "@/components/dashboard/charts/StackedBar";
import { KpiCard } from "@/components/dashboard/KpiCard";
import {
  toIncidentStatusView,
  toPlatformHealthView,
  toRfpView,
  toStockView,
} from "@/components/dashboard/selectors";
import { sharedRequest } from "@/components/dashboard/requestQueue";
import type { Tone } from "@/components/dashboard/tones";
import { useAsyncQuery } from "@/hooks/useAsyncQuery";
import { fetchIncidentSummary, friendlyIncidentError } from "@/lib/services/incidentsManagerApi";
import { fetchMedicalSupplies, friendlyInventoryError } from "@/lib/services/inventoryApi";
import { friendlyRfpError, listRfpTickets } from "@/lib/services/rfpApi";
import { fetchTelemetryReport, friendlyTelemetryError } from "@/lib/services/telemetryApi";

/* Module-level query/error functions keep useAsyncQuery dependencies stable. */
const loadIncidents = async () => toIncidentStatusView(await sharedRequest("incident-summary", fetchIncidentSummary));
const incidentsError = (err: unknown) => friendlyIncidentError(err, "Could not load incidents.");

const loadRfps = async () => toRfpView(await sharedRequest("rfp-tickets", listRfpTickets), new Date());
const rfpsError = (err: unknown) => friendlyRfpError(err, "Could not load RFP tickets.");

const loadStock = async () => toStockView(await sharedRequest("medical-supplies", fetchMedicalSupplies));
const stockError = (err: unknown) => friendlyInventoryError(err, "Could not load supplies.");

const loadHealth = async () => toPlatformHealthView(await sharedRequest("telemetry-report", () => fetchTelemetryReport()));
const healthError = (err: unknown) => friendlyTelemetryError(err, "Could not load telemetry.");

const formatNumber = (value: number) => value.toLocaleString("en-US");
const formatPercent = (rate: number) => `${(rate * 100).toFixed(1)}%`;

function OpenIncidentsKpi() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadIncidents, resolveError: incidentsError });
  return (
    <KpiCard
      label="Open incidents"
      href="/incidents"
      status={status}
      error={error}
      onRetry={reload}
      value={data ? formatNumber(data.active) : undefined}
      unit="active"
      badge={data ? { text: `${formatNumber(data.total)} total`, tone: "neutral" } : undefined}
      chart={
        data ? (
          <Donut
            label="Incidents by status"
            size={56}
            segments={[
              { label: "Open", value: data.open, tone: "danger" },
              { label: "In progress", value: data.inProgress, tone: "warning" },
              { label: "Resolved", value: data.resolved, tone: "success" },
            ]}
          />
        ) : undefined
      }
    />
  );
}

function RfpAwaitingKpi() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadRfps, resolveError: rfpsError });
  return (
    <KpiCard
      label="RFPs awaiting action"
      href="/rfp"
      status={status}
      error={error}
      onRetry={reload}
      value={data ? formatNumber(data.awaiting) : undefined}
      unit="tickets"
      badge={
        data
          ? data.awaiting > 0
            ? { text: "Needs review", tone: "warning" }
            : { text: "All clear", tone: "success" }
          : undefined
      }
      detail={
        data
          ? `${data.waitingForApproval} approval · ${data.needsReview} human review · ${data.receivedInWindow} received in 8 weeks`
          : undefined
      }
      chart={data ? <Sparkline values={data.weekly} label="RFP tickets received per week, last 8 weeks" /> : undefined}
    />
  );
}

function SuppliesKpi() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadStock, resolveError: stockError });
  return (
    <KpiCard
      label="Supplies low or critical"
      href="/inventory/products"
      status={status}
      error={error}
      onRetry={reload}
      value={data ? formatNumber(data.low + data.critical) : undefined}
      unit={data ? `of ${formatNumber(data.total)} SKUs` : "SKUs"}
      badge={
        data
          ? data.critical > 0
            ? { text: `${data.critical} critical`, tone: "danger" }
            : { text: "No critical", tone: "success" }
          : undefined
      }
      chart={
        data ? (
          <StackedBar
            label="Supplies by stock level"
            segments={[
              { label: "Critical", value: data.critical, tone: "danger" },
              { label: "Low", value: data.low, tone: "warning" },
              { label: "Healthy", value: data.healthy, tone: "success" },
            ]}
          />
        ) : undefined
      }
    />
  );
}

function authTone(rate: number | null): Tone {
  if (rate === null) return "neutral";
  if (rate > 0.1) return "danger";
  if (rate > 0.02) return "warning";
  return "success";
}

function PlatformHealthKpi() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadHealth, resolveError: healthError });
  return (
    <KpiCard
      label="Platform activity (7d)"
      href="/telemetry"
      status={status}
      error={error}
      onRetry={reload}
      value={data ? formatNumber(data.totalEvents) : undefined}
      unit="events"
      badge={
        data && data.authFailureRate !== null
          ? { text: `${formatPercent(data.authFailureRate)} auth fail`, tone: authTone(data.authFailureRate) }
          : undefined
      }
      detail={
        data
          ? `Avg latency ${data.avgLatencyMs === null ? "—" : `${Math.round(data.avgLatencyMs)} ms`} · ${formatNumber(data.authAttempts)} sign-in attempts`
          : undefined
      }
      chart={data ? <Sparkline values={data.eventsPerDay} label="Events per day, last 7 days" tone="info" /> : undefined}
    />
  );
}

/** Row of four KPI tiles; each tile loads and fails independently. */
export function DashboardKpis() {
  return (
    <section aria-labelledby="dashboard-kpis-heading">
      <h2 id="dashboard-kpis-heading" className="sr-only">
        Key indicators
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <OpenIncidentsKpi />
        <RfpAwaitingKpi />
        <SuppliesKpi />
        <PlatformHealthKpi />
      </div>
    </section>
  );
}
