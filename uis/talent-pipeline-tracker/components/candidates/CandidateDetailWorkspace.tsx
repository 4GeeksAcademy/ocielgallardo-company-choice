"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { Application, Note, RecordCreateInput } from "@/lib/types/application";
import { ApiError } from "@/lib/api/client";
import {
  fetchRecordById,
  patchRecord,
  updateRecord,
} from "@/lib/api/records";
import { createNote, deleteNote, fetchNotes } from "@/lib/api/notes";
import { AppHeader } from "@/components/layout/AppHeader";
import { ApplicationDetailPanel } from "@/components/detail/ApplicationDetailPanel";
import { ApplicationForm } from "@/components/forms/ApplicationForm";

export function CandidateDetailWorkspace() {
  const params = useParams<{ id: string }>();
  const candidateId = params.id;

  const [application, setApplication] = useState<Application | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    let isActive = true;

    async function loadCandidate() {
      setIsLoading(true);
      setNotesLoading(true);
      setError(null);
      setIsEditing(false);

      try {
        const [record, recordNotes] = await Promise.all([
          fetchRecordById(candidateId),
          fetchNotes(candidateId),
        ]);

        if (!isActive) return;

        setApplication(record);
        setNotes(
          recordNotes.sort((a, b) => b.created_at.localeCompare(a.created_at))
        );
      } catch (err) {
        if (!isActive) return;
        const message =
          err instanceof ApiError
            ? err.message
            : "No se pudo cargar la candidatura.";
        setError(message);
        setApplication(null);
        setNotes([]);
      } finally {
        if (isActive) {
          setIsLoading(false);
          setNotesLoading(false);
        }
      }
    }

    void loadCandidate();
    return () => {
      isActive = false;
    };
  }, [candidateId]);

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
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!application) return;
    await deleteNote(application.id, noteId);
    setNotes((current) => current.filter((note) => note.id !== noteId));
    setApplication({
      ...application,
      notes_count: Math.max(0, application.notes_count - 1),
    });
  };

  const handleEdit = async (data: RecordCreateInput) => {
    if (!application) return;
    setIsSubmittingForm(true);
    try {
      await updateRecord(application.id, data);
      const refreshed = await fetchRecordById(application.id);
      setApplication(refreshed);
      setIsEditing(false);
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

        {error && (
          <div
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            {error}
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
        ) : (
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
              notesLoading={notesLoading}
              isUpdating={isUpdating}
              isSubmittingNote={isSubmittingNote}
              onEdit={() => setIsEditing(true)}
              onStatusChange={handleStatusChange}
              onStageChange={handleStageChange}
              onAddNote={handleAddNote}
              onDeleteNote={handleDeleteNote}
            />
          </>
        )}
      </main>
    </div>
  );
}
