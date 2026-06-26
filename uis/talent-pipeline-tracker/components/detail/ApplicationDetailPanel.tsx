"use client";

import { useState } from "react";
import type { Application, Note } from "@/lib/types/application";
import { Button } from "@/components/ui/Button";
import { StatusStageBadge } from "@/components/applications/StatusStageBadge";
import { StatusStageControls } from "./StatusStageControls";
import { NotesSection } from "./NotesSection";

interface ApplicationDetailPanelProps {
  application: Application | null;
  notes: Note[];
  notesLoading: boolean;
  isUpdating: boolean;
  isSubmittingNote: boolean;
  onClose?: () => void;
  onEdit: () => void;
  onStatusChange: (status: Application["status"]) => Promise<void>;
  onStageChange: (stage: Application["stage"]) => Promise<void>;
  onAddNote: (content: string) => Promise<void>;
  onDeleteNote: (noteId: string) => Promise<void>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "long",
  }).format(new Date(value));
}

export function ApplicationDetailPanel({
  application,
  notes,
  notesLoading,
  isUpdating,
  isSubmittingNote,
  onClose,
  onEdit,
  onStatusChange,
  onStageChange,
  onAddNote,
  onDeleteNote,
}: ApplicationDetailPanelProps) {
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!application) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center">
        <div>
          <p className="font-medium text-slate-800">Selecciona una candidatura</p>
          <p className="mt-1 text-sm text-slate-600">
            Elige un candidato del listado para ver su detalle y gestionar su pipeline.
          </p>
        </div>
      </div>
    );
  }

  const handleStatusChange = async (status: Application["status"]) => {
    setFeedback(null);
    try {
      await onStatusChange(status);
      setFeedback("Estado actualizado correctamente.");
    } catch {
      setFeedback("No se pudo actualizar el estado.");
    }
  };

  const handleStageChange = async (stage: Application["stage"]) => {
    setFeedback(null);
    try {
      await onStageChange(stage);
      setFeedback("Etapa actualizada correctamente.");
    } catch {
      setFeedback("No se pudo actualizar la etapa.");
    }
  };

  return (
    <article className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4 sm:px-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-900">
              {application.full_name}
            </h2>
            <p className="text-sm text-slate-600">{application.position}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusStageBadge type="status" value={application.status} />
              <StatusStageBadge type="stage" value={application.stage} />
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            {application.cv_url && (
              <Button
                variant="primary"
                type="button"
                onClick={() => window.open(application.cv_url!, "_blank", "noopener,noreferrer")}
              >
                Ver CV
              </Button>
            )}
            <Button variant="secondary" onClick={onEdit}>
              Editar
            </Button>
            {onClose && (
              <Button variant="ghost" onClick={onClose} aria-label="Cerrar detalle">
                ✕
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4 sm:px-5">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="font-medium text-slate-900">{application.email}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Teléfono</dt>
            <dd className="font-medium text-slate-900">{application.phone}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Experiencia</dt>
            <dd className="font-medium text-slate-900">
              {application.experience_years} años
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Fecha de candidatura</dt>
            <dd className="font-medium text-slate-900">
              {formatDate(application.applied_at)}
            </dd>
          </div>
          {application.linkedin_url && (
            <div className="sm:col-span-2">
              <dt className="text-slate-500">LinkedIn</dt>
              <dd>
                <a
                  href={application.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-blue-600 hover:underline"
                >
                  Ver perfil
                </a>
              </dd>
            </div>
          )}
          <div className="sm:col-span-2">
            <dt className="text-slate-500">CV</dt>
            <dd>
              {application.cv_url ? (
                <a
                  href={application.cv_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-blue-600 hover:underline"
                >
                  Descargar o ver currículum
                </a>
              ) : (
                <span className="text-slate-500">No disponible</span>
              )}
            </dd>
          </div>
        </dl>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-900">
            Actualizar pipeline
          </h3>
          <StatusStageControls
            status={application.status}
            stage={application.stage}
            isUpdating={isUpdating}
            onStatusChange={handleStatusChange}
            onStageChange={handleStageChange}
          />
          {feedback && (
            <p className="text-sm text-slate-600" aria-live="polite">
              {feedback}
            </p>
          )}
        </div>

        <NotesSection
          notes={notes}
          isLoading={notesLoading}
          isSubmitting={isSubmittingNote}
          onAddNote={onAddNote}
          onDeleteNote={onDeleteNote}
        />
      </div>
    </article>
  );
}
