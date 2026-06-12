/** Recorre la lista y retorna el primer elemento que cumple el predicado. */
export function busquedaLineal<T>(items: T[], predicado: (item: T) => boolean): T | undefined {
  for (const item of items) {
    if (predicado(item)) return item;
  }
  return undefined;
}

/** Atajo para buscar por igualdad de un campo especifico. */
export function busquedaLinealPorCampo<T, K extends keyof T>(
  items: T[],
  campo: K,
  valor: T[K]
): T | undefined {
  return busquedaLineal(items, (item) => item[campo] === valor);
}

/**
 * Busca un numero en una lista ordenada usando busqueda binaria.
 * Requiere que `itemsOrdenados` este previamente ordenado por `obtenerValor`.
 */
export function busquedaBinariaPorNumero<T>(
  itemsOrdenados: T[],
  obtenerValor: (item: T) => number,
  objetivo: number
): T | undefined {
  let izquierda = 0;
  let derecha = itemsOrdenados.length - 1;

  // Reduce el rango de busqueda a la mitad en cada iteracion.
  while (izquierda <= derecha) {
    const medio = Math.floor((izquierda + derecha) / 2);
    const valor = obtenerValor(itemsOrdenados[medio]);

    if (valor === objetivo) return itemsOrdenados[medio];
    if (valor < objetivo) izquierda = medio + 1;
    else derecha = medio - 1;
  }

  return undefined;
}
