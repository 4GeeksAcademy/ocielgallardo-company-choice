"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

interface NoteFormProps {
  onSubmit: (content: string) => Promise<void>;
  isSubmitting: boolean;
}

export function NoteForm({ onSubmit, isSubmitting }: NoteFormProps) {
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setStatusMessage(null);

    if (!content.trim()) {
      setError("Escribe el contenido de la nota.");
      return;
    }

    try {
      await onSubmit(content.trim());
      setContent("");
      setStatusMessage("Nota añadida correctamente.");
    } catch {
      setError("No se pudo guardar la nota.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="space-y-1.5">
        <label htmlFor="note-content" className="block text-sm font-medium text-slate-700">
          Nueva nota
        </label>
        <textarea
          id="note-content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={3}
          placeholder="Añade observaciones de entrevista, seguimiento o decisión..."
          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20"
          aria-invalid={Boolean(error)}
        />
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        {statusMessage && (
          <p className="text-sm text-emerald-700" aria-live="polite">
            {statusMessage}
          </p>
        )}
      </div>
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Guardando..." : "Añadir nota"}
      </Button>
    </form>
  );
}
