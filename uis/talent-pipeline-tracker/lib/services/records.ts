import { apiRequest } from "./client";
import type {
  Application,
  RecordCreateInput,
  RecordPatchInput,
  RecordsListResponse,
} from "@/types/application";

export async function fetchRecords(limit = 100): Promise<Application[]> {
  const response = await apiRequest<RecordsListResponse>(
    `/records?limit=${limit}&page=1`
  );
  return response.data;
}

export async function fetchRecordById(id: string): Promise<Application> {
  return apiRequest<Application>(`/records/${id}`);
}

export async function createRecord(
  input: RecordCreateInput
): Promise<Application> {
  return apiRequest<Application>("/records", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateRecord(
  id: string,
  input: RecordCreateInput
): Promise<Application> {
  return apiRequest<Application>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export async function patchRecord(
  id: string,
  input: RecordPatchInput
): Promise<Application> {
  return apiRequest<Application>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}
