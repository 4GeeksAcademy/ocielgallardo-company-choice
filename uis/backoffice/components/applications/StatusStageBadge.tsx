import type { ApplicationStage, ApplicationStatus } from "@/types/application";
import {
  STAGE_BADGE_CLASSES,
  STAGE_LABELS,
  STATUS_BADGE_CLASSES,
  STATUS_LABELS,
} from "@/lib/constants/pipeline";
import { Badge } from "@/components/ui/Badge";

interface StatusStageBadgeProps {
  type: "status" | "stage";
  value: ApplicationStatus | ApplicationStage;
}

export function StatusStageBadge({ type, value }: StatusStageBadgeProps) {
  if (type === "status") {
    const status = value as ApplicationStatus;
    return (
      <Badge className={STATUS_BADGE_CLASSES[status]}>
        {STATUS_LABELS[status]}
      </Badge>
    );
  }

  const stage = value as ApplicationStage;
  return (
    <Badge className={STAGE_BADGE_CLASSES[stage]}>
      {STAGE_LABELS[stage]}
    </Badge>
  );
}
