"use client";

import { useMemo, useState } from "react";
import type {
  Appointment,
  Invoice,
  NoShowPrediction,
  Patient,
} from "../../../../src/types/models";
import { sortByField } from "../../../../src/utils/collections";
import { linearSearchByField } from "../../../../src/utils/search";
import {
  calculateAverage,
  calculateInvoiceRejectionRate,
  calculateNoShowRate,
  calculateTotal,
} from "../../../../src/utils/transformations";
import { validateInvoice } from "../../../../src/utils/validations";

const patients: Patient[] = [
  {
    patientId: "pat-1001",
    fullName: "Ava Thompson",
    phone: "+1 555-212-1001",
    email: "ava.thompson@example.com",
    medicalHistorySummary: "Type 2 diabetes follow-up.",
    clinicSite: "Austin Downtown",
    country: "US",
    status: "active",
  },
  {
    patientId: "pat-1002",
    fullName: "Liam Turner",
    phone: "+44 20 5555 1002",
    email: "liam.turner@example.co.uk",
    medicalHistorySummary: "Hypertension monitoring.",
    clinicSite: "London Central",
    country: "United Kingdom",
    status: "active",
  },
  {
    patientId: "pat-1003",
    fullName: "Mia Jackson",
    medicalHistorySummary: "Preventive annual check-up.",
    clinicSite: "Houston Memorial",
    country: "US",
    status: "inactive",
  },
];

const appointments: Appointment[] = [
  {
    appointmentId: "apt-2001",
    patientId: "pat-1001",
    dateISO: "2026-07-16T09:00:00.000Z",
    clinicSite: "Austin Downtown",
    country: "US",
    category: "Patient Experience and Access",
    status: "confirmed",
    noShowProbability: 0.21,
  },
  {
    appointmentId: "apt-2002",
    patientId: "pat-1002",
    dateISO: "2026-07-16T14:30:00.000Z",
    clinicSite: "London Central",
    country: "United Kingdom",
    category: "Patient Experience and Access",
    status: "no-show",
    noShowProbability: 0.39,
  },
  {
    appointmentId: "apt-2003",
    patientId: "pat-1003",
    dateISO: "2026-07-17T11:00:00.000Z",
    clinicSite: "Houston Memorial",
    country: "US",
    category: "Patient Experience and Access",
    status: "scheduled",
    noShowProbability: 0.15,
  },
];

const noShowPredictions: NoShowPrediction[] = [
  {
    predictionId: "nsp-1",
    appointmentId: "apt-2001",
    probability: 0.21,
    criticalThreshold: 0.22,
    isCritical: false,
    recommendedAction: "confirmation",
    status: "pending",
  },
  {
    predictionId: "nsp-2",
    appointmentId: "apt-2002",
    probability: 0.39,
    criticalThreshold: 0.22,
    isCritical: true,
    recommendedAction: "reschedule",
    status: "actioned",
  },
];

const invoices: Invoice[] = [
  {
    invoiceId: "inv-3001",
    patientId: "pat-1001",
    issueDateISO: "2026-07-10",
    category: "Revenue Cycle and Billing",
    status: "submitted",
    amount: 220,
    currency: "USD",
    billingCodes: ["99213"],
    rejectionProbability: 0.16,
  },
  {
    invoiceId: "inv-3002",
    patientId: "pat-1002",
    issueDateISO: "2026-07-11",
    category: "Revenue Cycle and Billing",
    status: "rejected",
    amount: 180,
    currency: "GBP",
    billingCodes: ["99214", "G0463"],
    rejectionProbability: 0.27,
  },
];

export function Hito2Playground() {
  const [patientQuery, setPatientQuery] = useState("pat-1002");

  const patientByLinearSearch = useMemo(
    () => linearSearchByField(patients, "patientId", patientQuery.trim()),
    [patientQuery]
  );

  const riskyAppointments = useMemo(
    () => sortByField(appointments, "noShowProbability", "desc").slice(0, 2),
    []
  );

  const invoiceValidation = useMemo(
    () =>
      validateInvoice(
        invoices[0],
        patients.find((patient) => patient.patientId === invoices[0].patientId)?.country
      ),
    []
  );

  const metrics = useMemo(
    () => ({
      noShowRate: calculateNoShowRate(appointments),
      rejectionRate: calculateInvoiceRejectionRate(invoices),
      avgNoShowRisk: calculateAverage(noShowPredictions, (item) => item.probability),
      totalInvoiceAmount: calculateTotal(invoices, (item) => item.amount),
    }),
    []
  );

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          Hito 2 Integration
        </p>
        <h2 className="mt-1 text-xl font-bold text-slate-900">
          Business Logic Playground (Shared TypeScript Utilities)
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          This block executes utilities imported directly from the root src folder.
          No business logic was duplicated in the Backoffice app.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="No-show rate" value={`${metrics.noShowRate}%`} />
        <MetricCard label="Invoice rejection rate" value={`${metrics.rejectionRate}%`} />
        <MetricCard label="Average no-show risk" value={`${(metrics.avgNoShowRisk * 100).toFixed(1)}%`} />
        <MetricCard label="Total invoice amount" value={`$${metrics.totalInvoiceAmount.toFixed(2)}`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Search Patients</h3>
          <label className="mt-3 block text-xs font-medium text-slate-600" htmlFor="patient-id-search">
            Patient ID
          </label>
          <input
            id="patient-id-search"
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            value={patientQuery}
            onChange={(event) => setPatientQuery(event.target.value)}
            placeholder="pat-1002"
          />
          <p className="mt-3 text-xs text-slate-600">
            linearSearchByField result: <span className="font-semibold text-slate-900">{patientByLinearSearch?.fullName ?? "Not found"}</span>
          </p>
        </article>

        <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-900">Filter Appointments</h3>
          <p className="mt-2 text-xs text-slate-600">Top 2 appointments sorted by no-show probability:</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {riskyAppointments.map((appointment) => (
              <li key={appointment.appointmentId}>
                - {appointment.appointmentId} · {(appointment.noShowProbability * 100).toFixed(0)}% risk · {appointment.status}
              </li>
            ))}
          </ul>
        </article>
      </div>

      <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h3 className="text-sm font-semibold text-slate-900">Validate Invoice</h3>
        <p className="mt-2 text-xs text-slate-600">
          Invoice checked: <span className="font-semibold text-slate-900">{invoices[0].invoiceId}</span>
        </p>
        {invoiceValidation.length === 0 ? (
          <p className="mt-2 text-sm font-medium text-emerald-700">No validation errors.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm text-red-700">
            {invoiceValidation.map((error) => (
              <li key={error}>- {error}</li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
}

function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-bold text-slate-900">{value}</p>
    </div>
  );
}
