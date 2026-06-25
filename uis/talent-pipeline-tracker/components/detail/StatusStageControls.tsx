"use client";

import type { ApplicationStage, ApplicationStatus } from "@/lib/types/application";
import {
  APPLICATION_STAGES,
  APPLICATION_STATUSES,
  STAGE_LABELS,
  STATUS_LABELS,
} from "@/lib/constants/pipeline";
import { Select } from "@/components/ui/Select";

interface StatusStageControlsProps {
  status: ApplicationStatus;
  stage: ApplicationStage;
  isUpdating: boolean;
  onStatusChange: (status: ApplicationStatus) => void;
  onStageChange: (stage: ApplicationStage) => void;
}

export function StatusStageControls({
  status,
  stage,
  isUpdating,
  onStatusChange,
  onStageChange,
}: StatusStageControlsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Select
        label="Estado"
        name="detail-status"
        value={status}
        disabled={isUpdating}
        onChange={(event) =>
          onStatusChange(event.target.value as ApplicationStatus)
        }
        options={APPLICATION_STATUSES.map((value) => ({
          value,
          label: STATUS_LABELS[value],
        }))}
      />
      <Select
        label="Etapa"
        name="detail-stage"
        value={stage}
        disabled={isUpdating}
        onChange={(event) =>
          onStageChange(event.target.value as ApplicationStage)
        }
        options={APPLICATION_STAGES.map((value) => ({
          value,
          label: STAGE_LABELS[value],
        }))}
      />
    </div>
  );
}
