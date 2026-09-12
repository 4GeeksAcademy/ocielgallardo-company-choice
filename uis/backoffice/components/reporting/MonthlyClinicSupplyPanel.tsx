"use client";

import { useCallback } from "react";
import { AsyncRequestPanel } from "@/components/ui/AsyncRequestPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAsyncQuery } from "@/hooks/useAsyncQuery";
import {
  fetchMonthlyClinicSupplyPerformance,
  friendlyReportingError,
} from "@/lib/services/reportingApi";
import type {
  ClinicSupplyPerformanceRow,
  MonthlyClinicSupplyPerformance,
} from "@/types/reporting";

/** "2026-07-01" → "July 2026" for a non-technical reader. */
function formatMonthLabel(monthStart: string | null): string {
  if (!monthStart) return "No period available";
  const parsed = new Date(`${monthStart}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return monthStart;
  return parsed.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function formatCurrency(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

function CountrySection({
  country,
  rows,
}: {
  country: string;
  rows: ClinicSupplyPerformanceRow[];
}) {
  if (rows.length === 0) return null;
  const currency = rows[0]?.currency ?? (country === "UK" ? "GBP" : "USD");
  const label =
    country === "US"
      ? "United States clinics (USD)"
      : country === "UK"
        ? "United Kingdom clinics (GBP)"
        : `${country} clinics`;

  const totalSpend = rows.reduce((sum, r) => sum + r.total_supply_cost, 0);
  const totalConsumption = rows.reduce(
    (sum, r) => sum + r.supply_consumption_count,
    0
  );
  const totalStockouts = rows.reduce(
    (sum, r) => sum + r.critical_stockout_count,
    0
  );
  const totalExpiry = rows.reduce((sum, r) => sum + r.expiry_risk_count, 0);

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 sm:p-5">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
        {label}
      </h2>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-200">
                Clinic
              </th>
              <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-200">
                Supply Cost per Clinic
              </th>
              <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-200">
                Supply Consumption Volume
              </th>
              <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-200">
                Critical Stockout Frequency
              </th>
              <th className="px-3 py-2 font-semibold text-slate-700 dark:text-slate-200">
                Expiry Risk Count
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={`${country}-${row.clinic_id}`}
                className="border-b border-slate-100 dark:border-slate-800"
              >
                <td className="px-3 py-2 font-medium text-slate-900 dark:text-slate-100">
                  Clinic {row.clinic_id}
                </td>
                <td className="px-3 py-2 text-slate-800 dark:text-slate-100">
                  {formatCurrency(row.total_supply_cost, row.currency)}
                </td>
                <td className="px-3 py-2 text-slate-800 dark:text-slate-100">
                  {row.supply_consumption_count.toLocaleString("en-US")}
                </td>
                <td className="px-3 py-2 text-slate-800 dark:text-slate-100">
                  {row.critical_stockout_count.toLocaleString("en-US")}
                </td>
                <td className="px-3 py-2 text-slate-800 dark:text-slate-100">
                  {row.expiry_risk_count.toLocaleString("en-US")}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-slate-300 font-semibold dark:border-slate-600">
              <td className="px-3 py-2 text-slate-900 dark:text-slate-50">
                Network total
              </td>
              <td className="px-3 py-2 text-slate-900 dark:text-slate-50">
                {formatCurrency(totalSpend, currency)}
              </td>
              <td className="px-3 py-2 text-slate-900 dark:text-slate-50">
                {totalConsumption.toLocaleString("en-US")}
              </td>
              <td className="px-3 py-2 text-slate-900 dark:text-slate-50">
                {totalStockouts.toLocaleString("en-US")}
              </td>
              <td className="px-3 py-2 text-slate-900 dark:text-slate-50">
                {totalExpiry.toLocaleString("en-US")}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

export function MonthlyClinicSupplyPanel() {
  const resolveError = useCallback(
    (err: unknown) =>
      friendlyReportingError(
        err,
        "Could not load the monthly clinic supply report. Check that the API and database are running, and that you are signed in."
      ),
    []
  );

  const queryFn = useCallback(
    () => fetchMonthlyClinicSupplyPerformance(),
    []
  );

  const { data, status, error, reload } =
    useAsyncQuery<MonthlyClinicSupplyPerformance>({ queryFn, resolveError });

  const usClinics =
    data?.clinics.filter((c) => c.country === "US") ?? [];
  const ukClinics =
    data?.clinics.filter((c) => c.country === "UK") ?? [];
  const otherClinics =
    data?.clinics.filter((c) => c.country !== "US" && c.country !== "UK") ?? [];

  return (
    <AsyncRequestPanel
      status={status}
      error={error}
      loadingMessage="Loading the Monthly Clinic Supply Performance report…"
      onRetry={() => void reload()}
    >
      {!data || data.clinics.length === 0 ? (
        <EmptyState
          title="No report data yet"
          description="No Monthly Clinic Supply Performance data has been computed. Run the pipeline for a month, then refresh."
          actionLabel="Retry"
          onAction={() => void reload()}
        />
      ) : (
        <div className="space-y-6">
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-100">
            <p className="font-semibold">Reporting period</p>
            <p className="mt-1 text-base">
              {formatMonthLabel(data.month_start)}
            </p>
            <p className="mt-1 text-xs opacity-80">
              Monthly supply cost, consumption activity, stockout, and expiry
              risk across the clinic network. US clinics are reported in USD and
              UK clinics in GBP — never combined.
            </p>
          </div>

          <CountrySection country="US" rows={usClinics} />
          <CountrySection country="UK" rows={ukClinics} />
          {otherClinics.map((row) => (
            <CountrySection
              key={`other-${row.clinic_id}`}
              country={row.country}
              rows={[row]}
            />
          ))}
        </div>
      )}
    </AsyncRequestPanel>
  );
}
