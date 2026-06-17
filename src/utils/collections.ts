import { CriticalFilter, NumericRange } from "../types/models";

// Contratos minimos requeridos para aplicar filtros por categoria, estado y probabilidad.
type WithCategory = { category: string };
type WithStatus = { status: string };
type WithProbability = { probability: number; isCritical?: boolean };

/** Direccion de ordenamiento permitida. */
export type SortDirection = "asc" | "desc";

/** Regla para ordenar por uno o mas campos. */
export interface SortRule<T> {
  field: keyof T;
  direction?: SortDirection;
}

/** Compara valores primitivos y retorna -1, 0 o 1. */
function compareValues(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === undefined || a === null) return -1;
  if (b === undefined || b === null) return 1;

  if (typeof a === "number" && typeof b === "number") {
    return a - b;
  }

  if (typeof a === "boolean" && typeof b === "boolean") {
    return Number(a) - Number(b);
  }

  return String(a).localeCompare(String(b));
}

/** Busca un unico elemento por un campo identificador (id). */
export function findOneById<T extends { [key: string]: string }>(
  items: T[],
  idField: keyof T,
  id: string
): T | undefined {
  return items.find((item) => item[idField] === id);
}

/** Filtra elementos por categoria exacta. */
export function filterByCategory<T extends WithCategory>(
  items: T[],
  category: string
): T[] {
  return items.filter((item) => item.category === category);
}

/** Filtra elementos por estado exacto. */
export function filterByStatus<T extends WithStatus>(
  items: T[],
  status: string
): T[] {
  return items.filter((item) => item.status === status);
}

/** Filtra elementos cuya probabilidad cae dentro de un rango min/max. */
export function filterByProbabilityRange<T extends WithProbability>(
  items: T[],
  range: NumericRange
): T[] {
  const min = range.min ?? Number.NEGATIVE_INFINITY;
  const max = range.max ?? Number.POSITIVE_INFINITY;
  return items.filter((item) => item.probability >= min && item.probability <= max);
}

/**
 * Aplica filtros combinados para consultas criticas:
 * - categoria
 * - estado
 * - rango de probabilidad
 * - solo elementos marcados como criticos
 */
export function filterCritical<T extends WithCategory & WithStatus & WithProbability>(
  items: T[],
  filters: CriticalFilter
): T[] {
  return items.filter((item) => {
    // Cada condicion descarta el elemento temprano para mantener la logica legible.
    if (filters.category && item.category !== filters.category) return false;
    if (filters.status && item.status !== filters.status) return false;

    if (filters.probabilityRange) {
      const { min, max } = filters.probabilityRange;
      if (min !== undefined && item.probability < min) return false;
      if (max !== undefined && item.probability > max) return false;
    }

    if (filters.onlyCritical && !item.isCritical) return false;
    return true;
  });
}

/** Ordena un array por un campo en orden ascendente o descendente. */
export function sortByField<T>(
  items: T[],
  field: keyof T,
  direction: SortDirection = "asc"
): T[] {
  const multiplier = direction === "asc" ? 1 : -1;
  return [...items].sort((left, right) => {
    const base = compareValues(left[field], right[field]);
    return base * multiplier;
  });
}

/**
 * Ordena un array por multiples campos en cascada.
 * Si el primer campo empata, se usa el siguiente, y asi sucesivamente.
 */
export function sortByMultipleFields<T>(items: T[], rules: SortRule<T>[]): T[] {
  if (rules.length === 0) return [...items];

  return [...items].sort((left, right) => {
    for (const rule of rules) {
      const direction = rule.direction ?? "asc";
      const multiplier = direction === "asc" ? 1 : -1;
      const base = compareValues(left[rule.field], right[rule.field]);
      if (base !== 0) return base * multiplier;
    }
    return 0;
  });
}
