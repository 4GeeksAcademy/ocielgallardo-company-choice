/** Departamentos clave elegidos para el proyecto. */
export type DepartamentoNombre =
  | "Experiencias del paciente y Acceso"
  | "Ciclo de Ingresos y Facturación";

/** Estados de avance del reto principal. */
export type EstadoReto = "pendiente" | "en-progreso" | "completado";

/** Estados posibles de una cita medica. */
export type EstadoCita =
  | "programada"
  | "confirmada"
  | "cancelada"
  | "no-show"
  | "completada";

/** Estados posibles de una factura en el ciclo de ingresos. */
export type EstadoFactura =
  | "borrador"
  | "enviada"
  | "aceptada"
  | "rechazada"
  | "pagada";

/** Estado operativo de una prediccion del agente. */
export type EstadoPrediccion = "pendiente" | "accionado" | "descartado";

/** Categorias de riesgo critico que monitorea el proyecto. */
export type CategoriaRiesgo = "no-show" | "rechazo-factura";

/** Datos base de la empresa seleccionada. */
export interface Empresa {
  id: string;
  nombre: "HealthCore";
  sector: "salud";
  razonEleccion: string;
  vision: string;
  aportePortafolio: string;
  trabajaConDatosSensibles: true;
}

/** Departamento de interes y su metrica principal. */
export interface DepartamentoInteres {
  id: string;
  nombre: DepartamentoNombre;
  problemaPrincipal: string;
  tasaActualPorcentaje: number;
}

/** Definicion del reto central del proyecto. */
export interface RetoProyecto {
  id: string;
  descripcion: "Sistema inteligente que predice pérdidas de ingresos y actúa automáticamente para evitarlas.";
  estado: EstadoReto;
}

/** Datos minimos de paciente para predicciones operativas. */
export interface Paciente {
  idPaciente: string;
  nombreCompleto: string;
  telefono?: string;
  email?: string;
  historialMedicoResumen: string;
  sede: string;
  pais: "EE.UU." | "Reino Unido";
  estado: "activo" | "inactivo";
}

/** Cita usada para modelar riesgo de no-show. */
export interface Cita {
  idCita: string;
  idPaciente: string;
  fechaISO: string;
  sede: string;
  pais: "EE.UU." | "Reino Unido";
  categoria: "Experiencias del paciente y Acceso";
  estado: EstadoCita;
  probabilidadNoShow: number;
}

/** Factura usada para modelar riesgo de rechazo. */
export interface Factura {
  idFactura: string;
  idPaciente: string;
  fechaEmisionISO: string;
  categoria: "Ciclo de Ingresos y Facturación";
  estado: EstadoFactura;
  monto: number;
  moneda: "USD" | "GBP";
  codigosFacturacion: string[];
  probabilidadRechazo: number;
}

/** Prediccion previa a la cita para prevenir no-shows. */
export interface PrediccionNoShow {
  idPrediccion: string;
  idCita: string;
  probabilidad: number;
  umbralCritico: number;
  esCritica: boolean;
  accionRecomendada: "recordatorio" | "confirmacion" | "reprogramacion";
  estado: EstadoPrediccion;
}

/** Prediccion previa al envio de factura para prevenir rechazos. */
export interface PrediccionRechazoFactura {
  idPrediccion: string;
  idFactura: string;
  probabilidad: number;
  umbralCritico: number;
  esCritica: boolean;
  accionRecomendada: "validar" | "corregir" | "enviar";
  estado: EstadoPrediccion;
}

/** Alerta operacional cuando una prediccion supera umbral critico. */
export interface AlertaCritica {
  idAlerta: string;
  categoria: CategoriaRiesgo;
  referenciaId: string;
  nivelRiesgo: number;
  estado: "abierta" | "en-proceso" | "cerrada";
  fechaISO: string;
}

/** Rango numerico util para filtros de probabilidad. */
export interface RangoNumerico {
  min?: number;
  max?: number;
}

/** Filtros combinables para consultas de elementos criticos. */
export interface FiltroCritico {
  categoria?: string;
  estado?: string;
  rangoProbabilidad?: RangoNumerico;
  soloCriticos?: boolean;
}
