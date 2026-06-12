import { CriticalFilter, NumericRange } from "../types/models";

// Contratos minimos requeridos para aplicar filtros por categoria, estado y probabilidad.
type WithCategory = { category: string };
type WithStatus = { status: string };
type WithProbability = { probability: number; isCritical?: boolean };

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
