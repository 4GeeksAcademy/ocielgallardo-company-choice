import type {
  IncidentAnalysisSummary,
  IncidentCategory,
  IncidentStatus,
  InvalidRuleKey,
} from "@/types/incidents";

const CATEGORIES: IncidentCategory[] = [
  "APPOINTMENT",
  "BILLING",
  "CLINICAL_CARE",
  "ACCESSIBILITY",
  "ADMINISTRATIVE",
];

const STATUSES: IncidentStatus[] = ["OPEN", "CLOSED", "DISCARDED"];

const INVALID_RULES: { key: InvalidRuleKey; label: string }[] = [
  { key: "invalid_clinic_id", label: "Invalid or missing clinic_id" },
  { key: "country_clinic_mismatch", label: "Country/clinic mismatch" },
  { key: "invalid_category", label: "Invalid or missing category" },
  { key: "empty_description", label: "Empty description" },
  { key: "missing_patient_id", label: "Missing patient_id" },
  { key: "closed_without_score", label: "Closed case, no score" },
];

const SCORE_LABELS: Record<number, string> = {
  1: "Very dissatisfied",
  2: "Dissatisfied",
  3: "Neutral",
  4: "Satisfied",
  5: "Very satisfied",
};

interface IncidentAnalysisSummaryProps {
  summary: IncidentAnalysisSummary;
}

function MetricRow({
  label,
  count,
  percentage,
}: {
  label: string;
  count: number;
  percentage?: number;
}) {
  return (
    <li className="flex items-center justify-between gap-3 border-b border-slate-100 py-2 text-sm last:border-b-0">
      <span className="text-slate-700">{label}</span>
      <span className="font-medium tabular-nums text-slate-900">
        {count}
        {percentage !== undefined ? (
          <span className="ml-2 text-slate-500">({percentage}%)</span>
        ) : null}
      </span>
    </li>
  );
}

export function IncidentAnalysisSummaryView({
  summary,
}: IncidentAnalysisSummaryProps) {
  const hasInvalid = summary.invalid > 0;

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          General metrics
        </h2>
        <dl className="mt-3 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-slate-50 px-3 py-2">
            <dt className="text-xs text-slate-500">Total records</dt>
            <dd className="text-2xl font-semibold tabular-nums text-slate-900">
              {summary.total}
            </dd>
          </div>
          <div className="rounded-lg bg-emerald-50 px-3 py-2">
            <dt className="text-xs text-emerald-700">Valid</dt>
            <dd className="text-2xl font-semibold tabular-nums text-emerald-900">
              {summary.valid}
            </dd>
          </div>
          <div
            className={`rounded-lg px-3 py-2 ${
              hasInvalid ? "bg-amber-50" : "bg-slate-50"
            }`}
          >
            <dt
              className={`text-xs ${
                hasInvalid ? "text-amber-700" : "text-slate-500"
              }`}
            >
              Invalid / incomplete
            </dt>
            <dd
              className={`text-2xl font-semibold tabular-nums ${
                hasInvalid ? "text-amber-900" : "text-slate-900"
              }`}
            >
              {summary.invalid}
            </dd>
          </div>
        </dl>
      </section>

      {hasInvalid ? (
        <section
          className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm sm:p-5"
          aria-live="polite"
        >
          <h2 className="text-sm font-semibold text-amber-900">
            Invalid records breakdown
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            This file contains {summary.invalid} invalid record
            {summary.invalid === 1 ? "" : "s"}. Counts by CONTEXT rule:
          </p>
          <ul className="mt-3 rounded-lg border border-amber-200 bg-white px-3">
            {INVALID_RULES.map(({ key, label }) => (
              <MetricRow
                key={key}
                label={label}
                count={summary.invalid_breakdown[key] ?? 0}
              />
            ))}
          </ul>
        </section>
      ) : (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          No invalid records in this file.
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Breakdown by category (valid)
          </h2>
          <ul className="mt-2">
            {CATEGORIES.map((name) => (
              <MetricRow
                key={name}
                label={name}
                count={summary.by_category[name]?.count ?? 0}
                percentage={summary.by_category[name]?.percentage ?? 0}
              />
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Breakdown by status (valid)
          </h2>
          <ul className="mt-2">
            {STATUSES.map((name) => (
              <MetricRow
                key={name}
                label={name}
                count={summary.by_status[name]?.count ?? 0}
                percentage={summary.by_status[name]?.percentage ?? 0}
              />
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Satisfaction index (closed cases)
        </h2>
        <p className="mt-2 text-sm text-slate-700">
          Scored cases:{" "}
          <span className="font-medium tabular-nums">
            {summary.satisfaction.scored_cases}
          </span>{" "}
          of{" "}
          <span className="font-medium tabular-nums">
            {summary.by_status.CLOSED?.count ?? 0}
          </span>
        </p>
        <p className="mt-1 text-sm text-slate-700">
          Average score:{" "}
          <span className="font-medium tabular-nums">
            {summary.satisfaction.average === null
              ? "—"
              : summary.satisfaction.average.toFixed(2)}
          </span>{" "}
          / 5.00
        </p>
        <ul className="mt-3">
          {[1, 2, 3, 4, 5].map((score) => (
            <MetricRow
              key={score}
              label={`Score ${score} (${SCORE_LABELS[score]})`}
              count={summary.satisfaction.histogram[score] ?? 0}
            />
          ))}
        </ul>
      </section>
    </div>
  );
}
