/** Recorre la lista y retorna el primer elemento que cumple el predicado. */
export function linearSearch<T>(items: T[], predicate: (item: T) => boolean): T | undefined {
  for (const item of items) {
    if (predicate(item)) return item;
  }
  return undefined;
}

/** Atajo para buscar por igualdad de un campo especifico. */
export function linearSearchByField<T, K extends keyof T>(
  items: T[],
  field: K,
  value: T[K]
): T | undefined {
  return linearSearch(items, (item) => item[field] === value);
}

/**
 * Busca un numero en una lista ordenada usando busqueda binaria.
 * Requiere que sortedItems este previamente ordenado por getValue.
 */
export function binarySearchByNumber<T>(
  sortedItems: T[],
  getValue: (item: T) => number,
  target: number
): T | undefined {
  let left = 0;
  let right = sortedItems.length - 1;

  // Reduce el rango de busqueda a la mitad en cada iteracion.
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const value = getValue(sortedItems[mid]);

    if (value === target) return sortedItems[mid];
    if (value < target) left = mid + 1;
    else right = mid - 1;
  }

  return undefined;
}
