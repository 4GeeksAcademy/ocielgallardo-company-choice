"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Application, Note, RecordCreateInput } from "@/lib/types/application";
import { ApiError } from "@/lib/api/client";
import {
  createRecord,
  fetchRecordById,
  fetchRecords,
  patchRecord,
  updateRecord,
} from "@/lib/api/records";
import { createNote, deleteNote, fetchNotes } from "@/lib/api/notes";
import { filterApplications } from "@/lib/utils/filterApplications";
import { AppHeader } from "@/components/layout/AppHeader";
import { ApplicationFilters } from "@/components/applications/ApplicationFilters";
import { ApplicationList } from "@/components/applications/ApplicationList";
import { ApplicationDetailPanel } from "@/components/detail/ApplicationDetailPanel";
import { ApplicationForm } from "@/components/forms/ApplicationForm";
import { Button } from "@/components/ui/Button";

type FormMode = "create" | "edit" | null;

function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

export function ApplicationsWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [records, setRecords] = useState<Application[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [queryInput, setQueryInput] = useState(searchParams.get("q") ?? "");

  const statusFilter = searchParams.get("status") ?? "";
  const stageFilter = searchParams.get("stage") ?? "";
  const selectedId = searchParams.get("selected");
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

  const loadRecords = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchRecords(100);
      setRecords(data);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "No se pudieron cargar las candidaturas.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isActive = true;

    async function bootstrap() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchRecords(100);
        if (isActive) setRecords(data);
      } catch (err) {
        if (!isActive) return;
        const message =
          err instanceof ApiError
            ? err.message
            : "No se pudieron cargar las candidaturas.";
        setError(message);
      } finally {
        if (isActive) setIsLoading(false);
      }
    }

    void bootstrap();
    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) return;

    let isActive = true;

    async function loadSelectedNotes() {
      setNotesLoading(true);
      try {
        const data = await fetchNotes(selectedId);
        if (isActive) {
          setNotes(data.sort((a, b) => b.created_at.localeCompare(a.created_at)));
        }
      } catch {
        if (isActive) setNotes([]);
      } finally {
        if (isActive) setNotesLoading(false);
      }
    }

    void loadSelectedNotes();
    return () => {
      isActive = false;
    };
  }, [selectedId]);

  const filteredRecords = useMemo(
    () =>
      filterApplications(records, {
        status: statusFilter,
        stage: stageFilter,
        query: debouncedQuery,
      }),
    [records, statusFilter, stageFilter, debouncedQuery]
  );

  const selectedRecord = useMemo(
    () => records.find((record) => record.id === selectedId) ?? null,
    [records, selectedId]
  );

  const updateRecordInState = (updated: Application) => {
    setRecords((current) =>
      current.map((record) => (record.id === updated.id ? updated : record))
    );
  };

  const handleSelect = (id: string) => {
    updateSearchParams({ selected: id });
    setFormMode(null);
  };

  const handleStatusChange = async (status: Application["status"]) => {
    if (!selectedRecord) return;
    const previous = selectedRecord;
    const optimistic = { ...selectedRecord, status };
    updateRecordInState(optimistic);
    setIsUpdating(true);
    try {
      const updated = await patchRecord(selectedRecord.id, { status });
      updateRecordInState(updated);
    } catch {
      updateRecordInState(previous);
      throw new Error("status update failed");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleStageChange = async (stage: Application["stage"]) => {
    if (!selectedRecord) return;
    const previous = selectedRecord;
    const optimistic = { ...selectedRecord, stage };
    updateRecordInState(optimistic);
    setIsUpdating(true);
    try {
      const updated = await patchRecord(selectedRecord.id, { stage });
      updateRecordInState(updated);
    } catch {
      updateRecordInState(previous);
      throw new Error("stage update failed");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddNote = async (content: string) => {
    if (!selectedRecord) return;
    setIsSubmittingNote(true);
    try {
      const note = await createNote(selectedRecord.id, content);
      setNotes((current) => [note, ...current]);
      updateRecordInState({
        ...selectedRecord,
        notes_count: selectedRecord.notes_count + 1,
      });
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!selectedRecord) return;
    await deleteNote(selectedRecord.id, noteId);
    setNotes((current) => current.filter((note) => note.id !== noteId));
    updateRecordInState({
      ...selectedRecord,
      notes_count: Math.max(0, selectedRecord.notes_count - 1),
    });
  };

  const handleCreate = async (data: RecordCreateInput) => {
    setIsSubmittingForm(true);
    try {
      const created = await createRecord(data);
      setRecords((current) => [created, ...current]);
      setFormMode(null);
      updateSearchParams({ selected: created.id });
    } finally {
      setIsSubmittingForm(false);
    }
  };

  const handleEdit = async (data: RecordCreateInput) => {
    if (!selectedRecord) return;
    setIsSubmittingForm(true);
    try {
      const updated = await updateRecord(selectedRecord.id, data);
      updateRecordInState(updated);
      setFormMode(null);
      const refreshed = await fetchRecordById(selectedRecord.id);
      updateRecordInState(refreshed);
    } finally {
      setIsSubmittingForm(false);
    }
  };

  const showMobileDetail = Boolean(selectedId);

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <AppHeader />

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              Pipeline de candidaturas
            </h2>
            <p className="text-sm text-slate-600">
              Gestión centralizada para el equipo de People &amp; Talent de HealthCore.
            </p>
          </div>
          <Button onClick={() => setFormMode("create")}>
            Nueva candidatura
          </Button>
        </div>

        {error && (
          <div
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            {error}
            <Button
              variant="ghost"
              className="ml-3 px-2 py-1 text-red-700"
              onClick={() => void loadRecords()}
            >
              Reintentar
            </Button>
          </div>
        )}

        {formMode && (
          <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
            <h3 className="mb-4 text-base font-semibold text-slate-900">
              {formMode === "create" ? "Registrar candidatura" : "Editar candidatura"}
            </h3>
            <ApplicationForm
              key={`${formMode}-${formMode === "edit" ? selectedRecord?.id : "new"}`}
              mode={formMode}
              initialData={formMode === "edit" ? selectedRecord : null}
              isSubmitting={isSubmittingForm}
              onSubmit={formMode === "create" ? handleCreate : handleEdit}
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

        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-5 lg:gap-5">
          <div
            className={`lg:col-span-2 ${showMobileDetail ? "hidden lg:block" : "block"}`}
          >
            <ApplicationList
              applications={filteredRecords}
              selectedId={selectedId}
              totalCount={records.length}
              onSelect={handleSelect}
              onCreate={() => setFormMode("create")}
              isLoading={isLoading}
            />
          </div>

          <div
            className={`lg:col-span-3 ${showMobileDetail ? "block" : "hidden lg:block"}`}
          >
            {showMobileDetail && (
              <div className="mb-3 lg:hidden">
                <Button
                  variant="secondary"
                  onClick={() => updateSearchParams({ selected: null })}
                >
                  ← Volver al listado
                </Button>
              </div>
            )}
            <ApplicationDetailPanel
              application={selectedRecord}
              notes={selectedId ? notes : []}
              notesLoading={notesLoading}
              isUpdating={isUpdating}
              isSubmittingNote={isSubmittingNote}
              onClose={
                showMobileDetail
                  ? () => updateSearchParams({ selected: null })
                  : undefined
              }
              onEdit={() => setFormMode("edit")}
              onStatusChange={handleStatusChange}
              onStageChange={handleStageChange}
              onAddNote={handleAddNote}
              onDeleteNote={handleDeleteNote}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
