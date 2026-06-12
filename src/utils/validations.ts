import {
  Cita,
  Factura,
  PrediccionNoShow,
  PrediccionRechazoFactura,
} from "../types/models";

/** Valida que una probabilidad sea numerica y este en rango [0, 1]. */
export function validarProbabilidad(valor: number, campo: string): string[] {
  const errores: string[] = [];
  if (Number.isNaN(valor)) errores.push(`${campo}: el valor no puede ser NaN.`);
  if (valor < 0 || valor > 1) errores.push(`${campo}: debe estar entre 0 y 1.`);
  return errores;
}

/** Valida campos minimos requeridos para una cita. */
export function validarCita(cita: Cita): string[] {
  const errores: string[] = [];
  if (!cita.idCita.trim()) errores.push("idCita es obligatorio.");
  if (!cita.idPaciente.trim()) errores.push("idPaciente es obligatorio.");
  if (!cita.fechaISO.trim()) errores.push("fechaISO es obligatoria.");
  errores.push(...validarProbabilidad(cita.probabilidadNoShow, "probabilidadNoShow"));
  return errores;
}

/** Valida campos minimos requeridos para una factura. */
export function validarFactura(factura: Factura): string[] {
  const errores: string[] = [];
  if (!factura.idFactura.trim()) errores.push("idFactura es obligatorio.");
  if (!factura.idPaciente.trim()) errores.push("idPaciente es obligatorio.");
  if (factura.monto <= 0) errores.push("monto debe ser mayor que 0.");
  if (factura.codigosFacturacion.length === 0) {
    errores.push("codigosFacturacion requiere al menos un codigo.");
  }
  errores.push(...validarProbabilidad(factura.probabilidadRechazo, "probabilidadRechazo"));
  return errores;
}

/**
 * Valida prediccion de no-show.
 * Regla clave: esCritica debe coincidir con probabilidad >= umbralCritico.
 */
export function validarPrediccionNoShow(prediccion: PrediccionNoShow): string[] {
  const errores = validarProbabilidad(prediccion.probabilidad, "probabilidad");
  errores.push(...validarProbabilidad(prediccion.umbralCritico, "umbralCritico"));

  const calculado = prediccion.probabilidad >= prediccion.umbralCritico;
  if (prediccion.esCritica !== calculado) {
    errores.push("esCritica debe coincidir con probabilidad >= umbralCritico.");
  }

  return errores;
}

/**
 * Valida prediccion de rechazo de factura.
 * Regla clave: esCritica debe coincidir con probabilidad >= umbralCritico.
 */
export function validarPrediccionRechazoFactura(
  prediccion: PrediccionRechazoFactura
): string[] {
  const errores = validarProbabilidad(prediccion.probabilidad, "probabilidad");
  errores.push(...validarProbabilidad(prediccion.umbralCritico, "umbralCritico"));

  const calculado = prediccion.probabilidad >= prediccion.umbralCritico;
  if (prediccion.esCritica !== calculado) {
    errores.push("esCritica debe coincidir con probabilidad >= umbralCritico.");
  }

  return errores;
}
