import type { Application } from "@/lib/types/application";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApplicationListItem } from "./ApplicationListItem";

interface ApplicationListProps {
  applications: Application[];
  selectedId: string | null;
  totalCount: number;
  onSelect: (id: string) => void;
  onCreate: () => void;
  isLoading: boolean;
}

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className="h-[76px] animate-pulse rounded-xl border border-slate-200 bg-slate-100"
        />
      ))}
    </div>
  );
}

export function ApplicationList({
  applications,
  selectedId,
  totalCount,
  onSelect,
  onCreate,
  isLoading,
}: ApplicationListProps) {
  return (
    <section className="flex min-h-0 flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-slate-600">
          <span className="font-semibold text-slate-900">
            {applications.length}
          </span>{" "}
          de {totalCount} candidaturas
        </p>
      </div>

      {isLoading ? (
        <ListSkeleton />
      ) : applications.length === 0 ? (
        <EmptyState
          title="Sin resultados"
          description="No hay candidaturas que coincidan con los filtros actuales."
          actionLabel="Registrar candidatura"
          onAction={onCreate}
        />
      ) : (
        <ul className="space-y-2 overflow-y-auto pr-1">
          {applications.map((application) => (
            <li key={application.id}>
              <ApplicationListItem
                application={application}
                isSelected={application.id === selectedId}
                onSelect={onSelect}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
