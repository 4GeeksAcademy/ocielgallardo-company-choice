"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { Application, RecordCreateInput } from "@/types/application";
import {
  fetchRecordById,
  patchRecord,
  updateRecord,
} from "@/lib/services/records";
import { createNote, deleteNote } from "@/lib/services/notes";
import { useCandidateDetail } from "@/hooks/useCandidateDetail";
import { AppHeader } from "@/components/layout/AppHeader";
import { ApplicationDetailPanel } from "@/components/detail/ApplicationDetailPanel";
import { ApplicationForm } from "@/components/forms/ApplicationForm";

interface CandidateDetailWorkspaceProps {
  candidateId: string;
}

type ActionFeedback = { type: "success" | "error"; message: string };

export function CandidateDetailWorkspace({
  candidateId,
}: CandidateDetailWorkspaceProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const {
    application,
    setApplication,
    notes,
    setNotes,
    isLoading,
    isRecordError,
    recordError,
    isNotesLoading,
    isNotesError,
    notesError,
    reloadNotes,
  } = useCandidateDetail(candidateId);

  const [isUpdating, setIsUpdating] = useState(false);
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<ActionFeedback | null>(
    () =>
      searchParams.get("created") === "1"
        ? {
            type: "success",
            message: "Candidatura registrada correctamente.",
          }
        : null
  );
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (searchParams.get("created") !== "1") return;
    router.replace(`/candidates/${candidateId}`, { scroll: false });
  }, [searchParams, candidateId, router]);

  const handleStatusChange = async (status: Application["status"]) => {
    if (!application) return;
    const previous = application;
    setApplication({ ...application, status });
    setIsUpdating(true);
    try {
      const updated = await patchRecord(application.id, { status });
      setApplication(updated);
    } catch {
      setApplication(previous);
      throw new Error("status update failed");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleStageChange = async (stage: Application["stage"]) => {
    if (!application) return;
    const previous = application;
    setApplication({ ...application, stage });
    setIsUpdating(true);
    try {
      const updated = await patchRecord(application.id, { stage });
      setApplication(updated);
    } catch {
      setApplication(previous);
      throw new Error("stage update failed");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleAddNote = async (content: string) => {
    if (!application) return;
    setIsSubmittingNote(true);
    try {
      const note = await createNote(application.id, content);
      setNotes((current) => [note, ...current]);
      setApplication({
        ...application,
        notes_count: application.notes_count + 1,
      });
    } catch (error) {
      throw error;
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!application) return;
    try {
      await deleteNote(application.id, noteId);
      setNotes((current) => current.filter((note) => note.id !== noteId));
      setApplication({
        ...application,
        notes_count: Math.max(0, application.notes_count - 1),
      });
    } catch (error) {
      throw error;
    }
  };

  const handleEdit = async (data: RecordCreateInput) => {
    if (!application) return;
    setIsSubmittingForm(true);
    setActionFeedback(null);
    try {
      await updateRecord(application.id, data);
      const refreshed = await fetchRecordById(application.id);
      setApplication(refreshed);
      setIsEditing(false);
      setActionFeedback({
        type: "success",
        message: "Candidatura actualizada correctamente.",
      });
    } catch (error) {
      setActionFeedback({
        type: "error",
        message: "No se pudieron guardar los cambios. Inténtalo de nuevo.",
      });
      throw error;
    } finally {
      setIsSubmittingForm(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <AppHeader />

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-3">
          <Link
            href="/applications"
            className="text-sm font-medium text-blue-600 hover:underline"
          >
            ← Volver al pipeline
          </Link>
        </div>

        {isRecordError && recordError && (
          <div
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            {recordError}
          </div>
        )}

        {actionFeedback && (
          <div
            role={actionFeedback.type === "error" ? "alert" : "status"}
            aria-live="polite"
            className={`rounded-lg border px-4 py-3 text-sm ${
              actionFeedback.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-red-200 bg-red-50 text-red-800"
            }`}
          >
            {actionFeedback.message}
          </div>
        )}

        {isLoading ? (
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
            <div className="h-8 w-2/3 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-slate-100" />
            <div className="grid gap-3 sm:grid-cols-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-12 animate-pulse rounded bg-slate-100"
                />
              ))}
            </div>
          </div>
        ) : !isRecordError ? (
          <>
            {isEditing && application && (
              <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
                <h3 className="mb-4 text-base font-semibold text-slate-900">
                  Editar candidatura
                </h3>
                <ApplicationForm
                  key={application.id}
                  mode="edit"
                  initialData={application}
                  isSubmitting={isSubmittingForm}
                  onSubmit={handleEdit}
                  onCancel={() => setIsEditing(false)}
                />
              </section>
            )}

            <ApplicationDetailPanel
              application={application}
              notes={notes}
              notesLoading={isNotesLoading}
              notesError={isNotesError ? notesError : null}
              onRetryNotes={() => void reloadNotes()}
              isUpdating={isUpdating}
              isSubmittingNote={isSubmittingNote}
              onEdit={() => setIsEditing(true)}
              onStatusChange={handleStatusChange}
              onStageChange={handleStageChange}
              onAddNote={handleAddNote}
              onDeleteNote={handleDeleteNote}
            />
          </>
        ) : null}
      </main>
    </div>
  );
}
