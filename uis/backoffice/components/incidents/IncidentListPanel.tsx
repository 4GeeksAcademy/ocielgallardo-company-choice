"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Select } from "@/components/ui/Select";
import {
  fetchIncidents,
  friendlyIncidentError,
  updateIncidentStatus,
} from "@/lib/services/incidentsManagerApi";
import type {
  IncidentBranch,
  IncidentListFilters,
  IncidentOrigin,
  IncidentStatus,
  ManagedIncident,
} from "@/types/incidentManager";
import {
  INCIDENT_BRANCH_OPTIONS,
  INCIDENT_ORIGIN_OPTIONS,
  INCIDENT_STATUS_OPTIONS,
  STATUS_TRANSITIONS,
  branchLabel,
  categoryLabel,
  originLabel,
  statusLabel,
} from "@/types/incidentManager";
import type { AsyncStatus } from "@/types/async";

function nextStatusOptions(current: IncidentStatus): IncidentStatus[] {
  return STATUS_TRANSITIONS[current] ?? [];
}

export function IncidentListPanel() {
  const [filters, setFilters] = useState<IncidentListFilters>({
    status: "",
    origin: "",
    branch: "",
  });
  const [applied, setApplied] = useState<IncidentListFilters>({
    status: "",
    origin: "",
    branch: "",
  });
  const [incidents, setIncidents] = useState<ManagedIncident[]>([]);
  const [status, setStatus] = useState<AsyncStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const load = useCallback(async (activeFilters: IncidentListFilters) => {
    setStatus("loading");
    setError(null);
    setActionError(null);
    try {
      const data = await fetchIncidents(activeFilters);
      setIncidents(data);
      setStatus("success");
    } catch (err) {
      setError(
        friendlyIncidentError(
          err,
          "Could not load incidents. Check that the API is running and try again."
        )
      );
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void load(applied);
  }, [applied, load]);

  async function handleStatusChange(
    incident: ManagedIncident,
    nextStatus: IncidentStatus
  ) {
    if (nextStatus === incident.status) {
      return;
    }
    const previous = incident.status;
    setActionError(null);
    setUpdatingId(incident.id);
    setIncidents((current) =>
      current.map((row) =>
        row.id === incident.id ? { ...row, status: nextStatus } : row
      )
    );

    try {
      const updated = await updateIncidentStatus(incident.id, {
        status: nextStatus,
      });
      setIncidents((current) =>
        current.map((row) => (row.id === updated.id ? updated : row))
      );
    } catch (err) {
      setIncidents((current) =>
        current.map((row) =>
          row.id === incident.id ? { ...row, status: previous } : row
        )
      );
      setActionError(
        friendlyIncidentError(
          err,
          "Could not update the status. The previous value was restored."
        )
      );
    } finally {
      setUpdatingId(null);
    }
  }

  if (status === "loading") {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 text-sm text-slate-600 dark:text-slate-300">
        Loading incidents…
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-6">
        <p className="text-sm text-red-700 dark:text-red-400" role="alert">
          {error}
        </p>
        <Button className="mt-4" type="button" onClick={() => void load(applied)}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <form
        className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 sm:grid-cols-4"
        onSubmit={(event) => {
          event.preventDefault();
          setApplied({ ...filters });
        }}
      >
        <Select
          label="Status"
          name="filter-status"
          value={filters.status ?? ""}
          onChange={(event) =>
            setFilters((current) => ({
              ...current,
              status: event.target.value as IncidentStatus | "",
            }))
          }
          options={[
            { value: "", label: "All statuses" },
            ...INCIDENT_STATUS_OPTIONS,
          ]}
        />
        <Select
          label="Origin"
          name="filter-origin"
          value={filters.origin ?? ""}
          onChange={(event) =>
            setFilters((current) => ({
              ...current,
              origin: event.target.value as IncidentOrigin | "",
            }))
          }
          options={[
            { value: "", label: "All origins" },
            ...INCIDENT_ORIGIN_OPTIONS,
          ]}
        />
        <Select
          label="Branch"
          name="filter-branch"
          value={filters.branch ?? ""}
          onChange={(event) =>
            setFilters((current) => ({
              ...current,
              branch: event.target.value as IncidentBranch | "",
            }))
          }
          options={[
            { value: "", label: "All branches" },
            ...INCIDENT_BRANCH_OPTIONS,
          ]}
        />
        <div className="flex items-end">
          <Button type="submit" className="w-full">
            Apply filters
          </Button>
        </div>
      </form>

      {actionError ? (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {actionError}
        </p>
      ) : null}

      {incidents.length === 0 ? (
        <EmptyState
          title="No incidents to show"
          description="There are no incidents for the current filters, or none have been registered yet."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Origin</th>
                <th className="px-3 py-2">Branch</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => {
                const options = nextStatusOptions(incident.status);
                return (
                  <tr key={incident.id} className="border-b border-slate-100 dark:border-slate-700">
                    <td className="px-3 py-2 font-mono text-xs text-slate-500 dark:text-slate-400">
                      {incident.id}
                    </td>
                    <td className="px-3 py-2">
                      <p className="font-medium text-slate-900 dark:text-slate-50">{incident.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">
                        {incident.description}
                      </p>
                    </td>
                    <td className="px-3 py-2">{categoryLabel(incident.category)}</td>
                    <td className="px-3 py-2">{originLabel(incident.origin)}</td>
                    <td className="px-3 py-2">{branchLabel(incident.branch)}</td>
                    <td className="px-3 py-2">
                      {options.length === 0 ? (
                        <span className="text-slate-700 dark:text-slate-200">
                          {statusLabel(incident.status)}
                        </span>
                      ) : (
                        <select
                          className="w-full rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
                          value={incident.status}
                          disabled={updatingId === incident.id}
                          aria-label={`Update status for incident ${incident.id}`}
                          onChange={(event) =>
                            void handleStatusChange(
                              incident,
                              event.target.value as IncidentStatus
                            )
                          }
                        >
                          <option value={incident.status}>
                            {statusLabel(incident.status)}
                          </option>
                          {options.map((value) => (
                            <option key={value} value={value}>
                              → {statusLabel(value)}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
