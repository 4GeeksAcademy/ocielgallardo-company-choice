import { FiltroCritico, RangoNumerico } from "../types/models";

// Contratos minimos para poder aplicar filtros por categoria, estado y probabilidad.
type ConCategoria = { categoria: string };
type ConEstado = { estado: string };
type ConProbabilidad = { probabilidad: number; esCritica?: boolean };

/** Busca un unico elemento por un campo identificador (id). */
export function buscarUnoPorId<T extends { [key: string]: string }>(
  items: T[],
  campoId: keyof T,
  id: string
): T | undefined {
  return items.find((item) => item[campoId] === id);
}

/** Filtra elementos por categoria exacta. */
export function filtrarPorCategoria<T extends ConCategoria>(
  items: T[],
  categoria: string
): T[] {
  return items.filter((item) => item.categoria === categoria);
}

/** Filtra elementos por estado exacto. */
export function filtrarPorEstado<T extends ConEstado>(
  items: T[],
  estado: string
): T[] {
  return items.filter((item) => item.estado === estado);
}

/** Filtra elementos cuyo valor de probabilidad cae dentro de un rango min/max. */
export function filtrarPorRangoProbabilidad<T extends ConProbabilidad>(
  items: T[],
  rango: RangoNumerico
): T[] {
  const min = rango.min ?? Number.NEGATIVE_INFINITY;
  const max = rango.max ?? Number.POSITIVE_INFINITY;
  return items.filter((item) => item.probabilidad >= min && item.probabilidad <= max);
}

/**
 * Aplica filtros combinados para consultas criticas:
 * - categoria
 * - estado
 * - rango de probabilidad
 * - solo elementos marcados como criticos
 */
export function filtrarCriticos<T extends ConCategoria & ConEstado & ConProbabilidad>(
  items: T[],
  filtros: FiltroCritico
): T[] {
  return items.filter((item) => {
    // Cada condicion invalida el item temprano para mantener la lectura simple.
    if (filtros.categoria && item.categoria !== filtros.categoria) return false;
    if (filtros.estado && item.estado !== filtros.estado) return false;

    if (filtros.rangoProbabilidad) {
      const { min, max } = filtros.rangoProbabilidad;
      if (min !== undefined && item.probabilidad < min) return false;
      if (max !== undefined && item.probabilidad > max) return false;
    }

    if (filtros.soloCriticos && !item.esCritica) return false;
    return true;
  });
}
