"use client";

import { BarList } from "@/components/dashboard/charts/BarList";
import { ColumnChart } from "@/components/dashboard/charts/ColumnChart";
import { Donut } from "@/components/dashboard/charts/Donut";
import { CardState, DashboardCard } from "@/components/dashboard/DashboardCard";
import {
  toClinicSupplyView,
  toMovementDays,
  toSupplierView,
  topEntries,
} from "@/components/dashboard/selectors";
import { sharedRequest } from "@/components/dashboard/requestQueue";
import { useAsyncQuery } from "@/hooks/useAsyncQuery";
import { HealthcoreApiError } from "@/lib/services/healthcoreClient";
import { fetchIncidentSummary, friendlyIncidentError } from "@/lib/services/incidentsManagerApi";
import { fetchInventoryOrders, friendlyInventoryError } from "@/lib/services/inventoryApi";
import { fetchMonthlyClinicSupplyPerformance, friendlyReportingError } from "@/lib/services/reportingApi";
import { fetchSuppliers } from "@/lib/services/suppliersApi";

/* Module-level query/error functions keep useAsyncQuery dependencies stable. */
const loadBranches = async () => topEntries((await sharedRequest("incident-summary", fetchIncidentSummary)).by_branch, 6);
const branchesError = (err: unknown) => friendlyIncidentError(err, "Could not load incidents.");

const loadMovement = async () => toMovementDays(await sharedRequest("inventory-orders", fetchInventoryOrders), new Date(), 14);
const movementError = (err: unknown) => friendlyInventoryError(err, "Could not load inventory orders.");

/** 404 / 503 mean "no computed month yet" or "reporting DB not configured" — shown as an empty state. */
const loadClinicSupply = async () => {
  try {
    return toClinicSupplyView(await sharedRequest("clinic-supply", () => fetchMonthlyClinicSupplyPerformance()));
  } catch (err) {
    if (err instanceof HealthcoreApiError && (err.status === 404 || err.status === 503)) {
      return null;
    }
    throw err;
  }
};
const clinicSupplyError = (err: unknown) => friendlyReportingError(err, "Could not load the clinic supply report.");

const loadSuppliers = async () => toSupplierView(await sharedRequest("suppliers", fetchSuppliers), new Date(), 60);
const suppliersError = (err: unknown) =>
  err instanceof HealthcoreApiError ? err.message || "Could not load suppliers." : "Could not load suppliers.";

function IncidentsByBranchCard() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadBranches, resolveError: branchesError });
  return (
    <DashboardCard title="Incidents by branch" subtitle="All statuses, top 6 branches" href="/incidents/summary" linkLabel="Summary">
      <CardState status={status} error={error} onRetry={reload} isEmpty={!data?.length} emptyMessage="No incidents recorded yet.">
        <BarList label="Incidents by branch" items={data ?? []} />
      </CardState>
    </DashboardCard>
  );
}

function InventoryMovementCard() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadMovement, resolveError: movementError });
  const hasMovement = (data ?? []).some((day) => day.inbound + day.outbound > 0);
  return (
    <DashboardCard title="Inventory movement" subtitle="Orders per day, last 14 days (UTC)" href="/inventory/orders" linkLabel="Order history">
      <CardState status={status} error={error} onRetry={reload} isEmpty={!hasMovement} emptyMessage="No inventory orders in the last 14 days.">
        <ColumnChart
          label="Inventory orders per day, last 14 days"
          categories={(data ?? []).map((day) => day.label)}
          series={[
            { label: "Inbound deliveries", tone: "primary", values: (data ?? []).map((day) => day.inbound) },
            { label: "Outbound consumption", tone: "warning", values: (data ?? []).map((day) => day.outbound) },
          ]}
        />
      </CardState>
    </DashboardCard>
  );
}

function formatMonth(monthStart: string | null): string {
  if (!monthStart) return "Latest month";
  return new Date(`${monthStart.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function ClinicSupplyCard() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadClinicSupply, resolveError: clinicSupplyError });
  return (
    <DashboardCard
      title="Critical stockouts by clinic"
      subtitle={data ? `${formatMonth(data.monthStart)} · ${data.clinicCount} clinics` : "Monthly clinic supply performance"}
      href="/reporting"
      linkLabel="Reporting"
    >
      <CardState
        status={status}
        error={error}
        onRetry={reload}
        isEmpty={!data || data.clinicCount === 0}
        emptyMessage="No computed reporting month available yet."
      >
        {data ? (
          <>
            <BarList label="Critical stockouts by clinic" items={data.stockoutsByClinic.map((item) => ({ ...item, tone: "danger" as const }))} />
            <p className="mt-4 text-xs text-slate-600 dark:text-slate-300">
              <span className="font-semibold text-slate-900 dark:text-slate-50">{data.totalStockouts}</span> critical stockouts ·{" "}
              <span className="font-semibold text-slate-900 dark:text-slate-50">{data.totalExpiryRisk}</span> items at expiry risk
            </p>
          </>
        ) : null}
      </CardState>
    </DashboardCard>
  );
}

function SuppliersCard() {
  const { data, status, error, reload } = useAsyncQuery({ queryFn: loadSuppliers, resolveError: suppliersError });
  return (
    <DashboardCard title="Suppliers" subtitle="Status and contract renewals in the next 60 days" href="/suppliers" linkLabel="Directory">
      <CardState status={status} error={error} onRetry={reload} isEmpty={!data || data.active + data.suspended === 0} emptyMessage="No suppliers registered yet.">
        {data ? (
          <div className="space-y-4">
            <Donut
              label="Suppliers by status"
              centerValue={String(data.active + data.suspended)}
              segments={[
                { label: "Active", value: data.active, tone: "success" },
                { label: "Suspended", value: data.suspended, tone: "neutral" },
              ]}
            />
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Upcoming renewals</h4>
              {data.renewals.length ? (
                <ul className="mt-2 divide-y divide-slate-100 text-sm dark:divide-slate-800">
                  {data.renewals.slice(0, 4).map((renewal) => (
                    <li key={renewal.id} className="flex items-center justify-between gap-3 py-1.5">
                      <span className="truncate text-slate-700 dark:text-slate-200">{renewal.name}</span>
                      <span className={`shrink-0 text-xs font-semibold tabular-nums ${renewal.daysLeft <= 14 ? "text-danger" : "text-slate-500 dark:text-slate-400"}`}>
                        {renewal.daysLeft === 0 ? "today" : `in ${renewal.daysLeft} d`}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">No renewals due in the next 60 days.</p>
              )}
            </div>
          </div>
        ) : null}
      </CardState>
    </DashboardCard>
  );
}

/** 2×2 grid of office-wide charts; each card loads and fails independently. */
export function OfficeCharts() {
  return (
    <section aria-labelledby="dashboard-charts-heading">
      <h2 id="dashboard-charts-heading" className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-50">
        Operations overview
      </h2>
      <div className="grid gap-4 lg:grid-cols-2">
        <IncidentsByBranchCard />
        <InventoryMovementCard />
        <ClinicSupplyCard />
        <SuppliersCard />
      </div>
    </section>
  );
}
