# CONTEXT — HealthCore (Pipeline de Desempeño de Negocio)

## Proyectos de Data Pipeline (Diseño · Implementación · Subflows y Tests)

<!-- hide -->

_These instructions are [available in English](./CONTEXT-healthcore-pipeline.md)._

<!-- endhide -->

Este archivo es autocontenido: te da todo lo necesario para acotar, construir y probar el pipeline de desempeño de negocio de HealthCore, sin tener que buscar en otros documentos. Se construye directamente sobre las métricas obligatorias ya definidas en tu `CONTEXT-healthcore.md` (telemetría) — léelo primero si no lo has hecho.

> ⚠️ **Nota regulatoria (HIPAA / UK GDPR):** este pipeline agrega únicamente datos de la cadena de suministro. Igual que en el sistema de telemetría, ningún resultado de este pipeline puede contener identificadores de paciente, diagnósticos, ni ningún dato real o simulado de PHI — todo aquí se agrega por `clinic` y `department`, nunca por paciente.

---

## 1. El entregable de negocio

La Dra. Okonkwo (CEO) quiere un **paquete mensual listo para la junta directiva** que pueda revisar sin que su equipo pase dos días consolidando hojas de cálculo — comparando costo de insumos y riesgo de quiebre de stock entre las 12 clínicas de la red, en EE.UU. y Reino Unido.

> **Entregable objetivo:** un consolidado mensual, por clínica y por país, de costo de insumos, actividad de quiebre de stock y riesgo de vencimiento — el "Reporte Mensual de Desempeño de Insumos por Clínica".

Este es el **único entregable concreto** para el que existe tu pipeline. Todo lo que escribas en tu `PIPELINE_DESIGN.md` debe poder rastrearse hasta aquí.

**Audiencia:** la Dra. Okonkwo (CEO) y Claire (Chief Compliance Officer) — stakeholders no técnicos que necesitan números, no eventos crudos.
**Frecuencia:** mensual (listo el primer día hábil del mes, alineado con la expectativa que ya tiene el liderazgo de un "paquete de reporte para la junta automático").

---

## 2. KPIs a medir

**Estos son los KPIs para los que existe este pipeline.** Todo lo demás en este documento — eventos de origen, lógica de agregación, esquema de tabla — es detalle de implementación al servicio de estos cuatro números. Si no tienes claro qué construir a continuación, vuelve a esta lista.

| KPI | Qué mide | Por qué le importa a HealthCore |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Costo de insumos por clínica** | Cuánto gastó una clínica comprando insumos médicos durante el mes. | Muestra dónde se concentra el gasto en toda la red y alimenta las decisiones de compra entre clínicas. |
| **Volumen de consumo de insumos** | Cuántos eventos de consumo de insumos registró una clínica durante el mes, por departamento. | La señal de actividad operativa — ayuda a distinguir una clínica genuinamente ocupada de un hueco de captura de datos. |
| **Frecuencia de quiebre crítico** | Cuántas veces durante el mes una clínica cayó por debajo del umbral mínimo de un insumo. | Una señal de riesgo de seguridad del paciente y de cumplimiento sobre la que Marcus y Claire necesitan actuar rápido. |

Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
Sin archivos seleccionados
Attach files by dragging & dropping, selecting or pasting them.
