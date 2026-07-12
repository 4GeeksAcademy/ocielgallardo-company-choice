import { apiRequest } from "./client";
import type { Note, NotesListResponse } from "@/types/application";

export async function fetchNotes(recordId: string): Promise<Note[]> {
  const response = await apiRequest<NotesListResponse>(
    `/records/${recordId}/notes`
  );
  return response.data;
}

export async function createNote(
  recordId: string,
  content: string
): Promise<Note> {
  return apiRequest<Note>(`/records/${recordId}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function deleteNote(
  recordId: string,
  noteId: string
): Promise<void> {
  await apiRequest<void>(`/records/${recordId}/notes/${noteId}`, {
    method: "DELETE",
  });
}
