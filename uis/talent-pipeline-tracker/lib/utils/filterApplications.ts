import type { Application } from "../types/application";

export interface ApplicationFilters {
  status: string;
  stage: string;
  query: string;
}

function filterByStatus(items: Application[], status: string): Application[] {
  if (!status) return items;
  return items.filter((item) => item.status === status);
}

function filterByStage(items: Application[], stage: string): Application[] {
  if (!stage) return items;
  return items.filter((item) => item.stage === stage);
}

function filterBySearch(items: Application[], query: string): Application[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return items;

  return items.filter(
    (item) =>
      item.full_name.toLowerCase().includes(normalized) ||
      item.email.toLowerCase().includes(normalized)
  );
}

export function filterApplications(
  items: Application[],
  filters: ApplicationFilters
): Application[] {
  let result = items;
  result = filterByStatus(result, filters.status);
  result = filterByStage(result, filters.stage);
  result = filterBySearch(result, filters.query);
  return result;
}
