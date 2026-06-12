import {
  AlertaCritica,
  Cita,
  Factura,
  PrediccionNoShow,
  PrediccionRechazoFactura,
} from "../types/models";

/** Calcula el porcentaje de citas marcadas como no-show. */
export function calcularTasaNoShow(citas: Cita[]): number {
  if (citas.length === 0) return 0;
  const noShows = citas.filter((cita) => cita.estado === "no-show").length;
  return Number(((noShows / citas.length) * 100).toFixed(2));
}

/** Calcula el porcentaje de facturas con estado rechazado. */
export function calcularTasaRechazoFacturas(facturas: Factura[]): number {
  if (facturas.length === 0) return 0;
  const rechazadas = facturas.filter((factura) => factura.estado === "rechazada").length;
  return Number(((rechazadas / facturas.length) * 100).toFixed(2));
}

/**
 * Convierte predicciones criticas en alertas operativas.
 * Genera alertas para riesgo de no-show y de rechazo de factura.
 */
export function generarAlertasCriticas(
  prediccionesNoShow: PrediccionNoShow[],
  prediccionesRechazo: PrediccionRechazoFactura[]
): AlertaCritica[] {
  // Alertas provenientes del flujo de citas.
  const alertasNoShow: AlertaCritica[] = prediccionesNoShow
    .filter((prediccion) => prediccion.esCritica)
    .map((prediccion) => ({
      idAlerta: `alerta-noshow-${prediccion.idPrediccion}`,
      categoria: "no-show",
      referenciaId: prediccion.idCita,
      nivelRiesgo: prediccion.probabilidad,
      estado: "abierta",
      fechaISO: new Date().toISOString(),
    }));

  // Alertas provenientes del flujo de facturacion.
  const alertasRechazo: AlertaCritica[] = prediccionesRechazo
    .filter((prediccion) => prediccion.esCritica)
    .map((prediccion) => ({
      idAlerta: `alerta-rechazo-${prediccion.idPrediccion}`,
      categoria: "rechazo-factura",
      referenciaId: prediccion.idFactura,
      nivelRiesgo: prediccion.probabilidad,
      estado: "abierta",
      fechaISO: new Date().toISOString(),
    }));

  return [...alertasNoShow, ...alertasRechazo];
}

/** Agrupa alertas por estado para simplificar reportes y dashboards. */
export function agruparAlertasPorEstado(alertas: AlertaCritica[]): Record<string, AlertaCritica[]> {
  return alertas.reduce<Record<string, AlertaCritica[]>>((acumulador, alerta) => {
    if (!acumulador[alerta.estado]) acumulador[alerta.estado] = [];
    acumulador[alerta.estado].push(alerta);
    return acumulador;
  }, {});
}
