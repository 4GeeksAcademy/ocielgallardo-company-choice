"use client";

import { useCallback, useEffect, useState } from "react";
import type { Application, Note } from "@/types/application";
import type { AsyncStatus } from "@/types/async";
import { ApiError } from "@/lib/services/client";
import { fetchRecordById } from "@/lib/services/records";
import { fetchNotes } from "@/lib/services/notes";

function resolveErrorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

function sortNotes(notes: Note[]): Note[] {
  return [...notes].sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export function useCandidateDetail(candidateId: string) {
  const [application, setApplication] = useState<Application | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [recordStatus, setRecordStatus] = useState<AsyncStatus>("loading");
  const [notesStatus, setNotesStatus] = useState<AsyncStatus>("loading");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [notesError, setNotesError] = useState<string | null>(null);

  const loadRecord = useCallback(async () => {
    setRecordStatus("loading");
    setRecordError(null);
    try {
      const record = await fetchRecordById(candidateId);
      setApplication(record);
      setRecordStatus("success");
    } catch (err) {
      setRecordError(
        resolveErrorMessage(err, "No se pudo cargar la candidatura.")
      );
      setApplication(null);
      setRecordStatus("error");
    }
  }, [candidateId]);

  const loadNotes = useCallback(async () => {
    setNotesStatus("loading");
    setNotesError(null);
    try {
      const recordNotes = await fetchNotes(candidateId);
      setNotes(sortNotes(recordNotes));
      setNotesStatus("success");
    } catch (err) {
      setNotesError(
        resolveErrorMessage(err, "No se pudieron cargar las notas internas.")
      );
      setNotes([]);
      setNotesStatus("error");
    }
  }, [candidateId]);

  useEffect(() => {
    let isActive = true;

    async function bootstrapRecord() {
      try {
        const record = await fetchRecordById(candidateId);
        if (!isActive) return;
        setApplication(record);
        setRecordStatus("success");
      } catch (err) {
        if (!isActive) return;
        setRecordError(
          resolveErrorMessage(err, "No se pudo cargar la candidatura.")
        );
        setApplication(null);
        setRecordStatus("error");
      }
    }

    async function bootstrapNotes() {
      try {
        const recordNotes = await fetchNotes(candidateId);
        if (!isActive) return;
        setNotes(sortNotes(recordNotes));
        setNotesStatus("success");
      } catch (err) {
        if (!isActive) return;
        setNotesError(
          resolveErrorMessage(err, "No se pudieron cargar las notas internas.")
        );
        setNotes([]);
        setNotesStatus("error");
      }
    }

    void bootstrapRecord();
    void bootstrapNotes();

    return () => {
      isActive = false;
    };
  }, [candidateId]);

  return {
    application,
    setApplication,
    notes,
    setNotes,
    recordStatus,
    notesStatus,
    isLoading: recordStatus === "loading",
    isRecordError: recordStatus === "error",
    isNotesLoading: notesStatus === "loading",
    isNotesError: notesStatus === "error",
    recordError,
    notesError,
    reloadRecord: loadRecord,
    reloadNotes: loadNotes,
  };
}
