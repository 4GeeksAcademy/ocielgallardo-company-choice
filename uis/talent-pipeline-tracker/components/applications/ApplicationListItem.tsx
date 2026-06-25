import type { Application } from "@/lib/types/application";
import { StatusStageBadge } from "./StatusStageBadge";

interface ApplicationListItemProps {
  application: Application;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export function ApplicationListItem({
  application,
  isSelected,
  onSelect,
}: ApplicationListItemProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(application.id)}
      className={`w-full rounded-xl border px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 ${
        isSelected
          ? "border-blue-300 bg-blue-50/70 shadow-sm"
          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-slate-900">
            {application.full_name}
          </p>
          <p className="truncate text-sm text-slate-600">
            {application.position}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <StatusStageBadge type="status" value={application.status} />
          <StatusStageBadge type="stage" value={application.stage} />
        </div>
      </div>
    </button>
  );
}
