"use client";

import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  APPLICATION_STAGES,
  APPLICATION_STATUSES,
  STAGE_LABELS,
  STATUS_LABELS,
} from "@/lib/constants/pipeline";

interface ApplicationFiltersProps {
  status: string;
  stage: string;
  query: string;
  onStatusChange: (value: string) => void;
  onStageChange: (value: string) => void;
  onQueryChange: (value: string) => void;
}

export function ApplicationFilters({
  status,
  stage,
  query,
  onStatusChange,
  onStageChange,
  onQueryChange,
}: ApplicationFiltersProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Input
        label="Search by name or email"
        name="search"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="e.g. Elena or elena@..."
      />
      <Select
        label="Status"
        name="status"
        value={status}
        onChange={(event) => onStatusChange(event.target.value)}
        options={[
          { value: "", label: "All statuses" },
          ...APPLICATION_STATUSES.map((value) => ({
            value,
            label: STATUS_LABELS[value],
          })),
        ]}
      />
      <Select
        label="Stage"
        name="stage"
        value={stage}
        onChange={(event) => onStageChange(event.target.value)}
        options={[
          { value: "", label: "All stages" },
          ...APPLICATION_STAGES.map((value) => ({
            value,
            label: STAGE_LABELS[value],
          })),
        ]}
      />
    </div>
  );
}
