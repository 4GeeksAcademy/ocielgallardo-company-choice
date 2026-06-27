"use client";

import { useState } from "react";
import type { Note } from "@/lib/types/application";
import { Button } from "@/components/ui/Button";
import { NoteForm } from "@/components/forms/NoteForm";

interface NotesSectionProps {
  notes: Note[];
  isLoading: boolean;
  isSubmitting: boolean;
  onAddNote: (content: string) => Promise<void>;
  onDeleteNote: (noteId: string) => Promise<void>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function NotesSection({
  notes,
  isLoading,
  isSubmitting,
  onAddNote,
  onDeleteNote,
}: NotesSectionProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDelete = async (noteId: string) => {
    if (!window.confirm("¿Eliminar esta nota interna?")) return;
    setDeletingId(noteId);
    setDeleteError(null);
    try {
      await onDeleteNote(noteId);
    } catch {
      setDeleteError("No se pudo eliminar la nota. Inténtalo de nuevo.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">Notas internas</h3>
        <p className="text-sm text-slate-600">
          Observaciones del equipo de People sobre esta candidatura.
        </p>
      </div>

      <NoteForm onSubmit={onAddNote} isSubmitting={isSubmitting} />

      {deleteError && (
        <p className="text-sm text-red-600" role="alert">
          {deleteError}
        </p>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, index) => (
            <div
              key={index}
              className="h-20 animate-pulse rounded-lg bg-slate-100"
            />
          ))}
        </div>
      ) : notes.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-200 px-4 py-6 text-center text-sm text-slate-500">
          Aún no hay notas para esta candidatura.
        </p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-800">{note.content}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatDate(note.created_at)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  className="shrink-0 px-2 py-1 text-xs text-red-600 hover:bg-red-50 hover:text-red-700"
                  disabled={deletingId === note.id}
                  onClick={() => handleDelete(note.id)}
                >
                  Eliminar
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
