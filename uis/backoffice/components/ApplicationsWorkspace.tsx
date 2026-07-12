"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { RecordCreateInput } from "@/types/application";
import { createRecord } from "@/lib/services/records";
import { filterApplications } from "@/lib/utils/filterApplications";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useRecords } from "@/hooks/useRecords";
import { ApplicationFilters } from "@/components/applications/ApplicationFilters";
import { ApplicationList } from "@/components/applications/ApplicationList";
import { ApplicationForm } from "@/components/forms/ApplicationForm";
import { Button } from "@/components/ui/Button";

type FormMode = "create" | null;

export function ApplicationsWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const { records, isLoading, isError, error, reload } = useRecords();
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [queryInput, setQueryInput] = useState(searchParams.get("q") ?? "");

  const statusFilter = searchParams.get("status") ?? "";
  const stageFilter = searchParams.get("stage") ?? "";
  const debouncedQuery = useDebouncedValue(queryInput);

  const updateSearchParams = useCallback(
    (updates: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      Object.entries(updates).forEach(([key, value]) => {
        if (!value) params.delete(key);
        else params.set(key, value);
      });
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    updateSearchParams({ q: debouncedQuery || null });
  }, [debouncedQuery, updateSearchParams]);

  const filteredRecords = useMemo(
    () =>
      filterApplications(records, {
        status: statusFilter,
        stage: stageFilter,
        query: debouncedQuery,
      }),
    [records, statusFilter, stageFilter, debouncedQuery]
  );

  const handleSelect = (id: string) => {
    setFormMode(null);
    router.push(`/candidates/${id}`);
  };

  const handleCreate = async (data: RecordCreateInput) => {
    setIsSubmittingForm(true);
    try {
      const created = await createRecord(data);
      setFormMode(null);
      router.push(`/candidates/${created.id}?created=1`);
    } catch (error) {
      throw error;
    } finally {
      setIsSubmittingForm(false);
    }
  };

  return (
    <div className="space-y-4">
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              Pipeline de candidaturas
            </h2>
            <p className="text-sm text-slate-600">
              Herramienta interna de Personas y Fuerza Laboral (Diane Foster) para
              cubrir perfiles clínicos en las 12 sedes de HealthCore.
            </p>
          </div>
          <Button onClick={() => setFormMode("create")}>
            Nueva candidatura
          </Button>
        </div>

        {formMode === "create" && (
          <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
            <h3 className="mb-4 text-base font-semibold text-slate-900">
              Registrar candidatura
            </h3>
            <ApplicationForm
              key="create"
              mode="create"
              initialData={null}
              isSubmitting={isSubmittingForm}
              onSubmit={handleCreate}
              onCancel={() => setFormMode(null)}
            />
          </section>
        )}

        <div className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
          <ApplicationFilters
            status={statusFilter}
            stage={stageFilter}
            query={queryInput}
            onStatusChange={(value) => updateSearchParams({ status: value || null })}
            onStageChange={(value) => updateSearchParams({ stage: value || null })}
            onQueryChange={setQueryInput}
          />
        </div>

        <ApplicationList
          applications={filteredRecords}
          selectedId={null}
          totalCount={records.length}
          onSelect={handleSelect}
          onCreate={() => setFormMode("create")}
          isLoading={isLoading}
          error={isError ? error : null}
          onRetry={() => void reload()}
        />
      </main>
    </div>
  );
}
