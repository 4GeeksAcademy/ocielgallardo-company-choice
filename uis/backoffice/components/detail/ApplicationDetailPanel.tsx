"use client";

import { useState } from "react";
import type { Application, Note } from "@/types/application";
import { Button } from "@/components/ui/Button";
import { StatusStageBadge } from "@/components/applications/StatusStageBadge";
import { StatusStageControls } from "./StatusStageControls";
import { NotesSection } from "./NotesSection";

interface ApplicationDetailPanelProps {
  application: Application | null;
  notes: Note[];
  notesLoading: boolean;
  notesError?: string | null;
  onRetryNotes?: () => void;
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
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "long",
  }).format(new Date(value));
}

export function ApplicationDetailPanel({
  application,
  notes,
  notesLoading,
  notesError,
  onRetryNotes,
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
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-xl border border-dashed border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-8 text-center">
        <div>
          <p className="font-medium text-slate-800 dark:text-slate-100">Select an application</p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Choose a candidate from the list to see their details and manage their pipeline.
          </p>
        </div>
      </div>
    );
  }

  const handleStatusChange = async (status: Application["status"]) => {
    setFeedback(null);
    try {
      await onStatusChange(status);
      setFeedback("Status updated.");
    } catch {
      setFeedback("Could not update the status.");
    }
  };

  const handleStageChange = async (stage: Application["stage"]) => {
    setFeedback(null);
    try {
      await onStageChange(stage);
      setFeedback("Stage updated.");
    } catch {
      setFeedback("Could not update the stage.");
    }
  };

  return (
    <article className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
      <div className="border-b border-slate-200 dark:border-slate-700 px-4 py-4 sm:px-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              {application.full_name}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">{application.position}</p>
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
                View CV
              </Button>
            )}
            <Button variant="secondary" onClick={onEdit}>
              Edit
            </Button>
            {onClose && (
              <Button variant="ghost" onClick={onClose} aria-label="Close details">
                ✕
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4 sm:px-5">
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Email</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-50">{application.email}</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Phone</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-50">{application.phone}</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Experience</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-50">
              {application.experience_years} years
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Application date</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-50">
              {formatDate(application.applied_at)}
            </dd>
          </div>
          {application.linkedin_url && (
            <div className="sm:col-span-2">
              <dt className="text-slate-500 dark:text-slate-400">LinkedIn</dt>
              <dd>
                <a
                  href={application.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-blue-600 dark:text-blue-300 hover:underline"
                >
                  View profile
                </a>
              </dd>
            </div>
          )}
          <div className="sm:col-span-2">
            <dt className="text-slate-500 dark:text-slate-400">CV</dt>
            <dd>
              {application.cv_url ? (
                <a
                  href={application.cv_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium text-blue-600 dark:text-blue-300 hover:underline"
                >
                  Download or view CV
                </a>
              ) : (
                <span className="text-slate-500 dark:text-slate-400">Not available</span>
              )}
            </dd>
          </div>
        </dl>

        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50">
            Update pipeline
          </h3>
          <StatusStageControls
            status={application.status}
            stage={application.stage}
            isUpdating={isUpdating}
            onStatusChange={handleStatusChange}
            onStageChange={handleStageChange}
          />
          {feedback && (
            <p className="text-sm text-slate-600 dark:text-slate-300" aria-live="polite">
              {feedback}
            </p>
          )}
        </div>

        <NotesSection
          notes={notes}
          isLoading={notesLoading}
          error={notesError}
          onRetry={onRetryNotes}
          isSubmitting={isSubmittingNote}
          onAddNote={onAddNote}
          onDeleteNote={onDeleteNote}
        />
      </div>
    </article>
  );
}
