# Plan de Telemetría HealthCore

**Compañía:** HealthCore  
**Hito:** Plan de Telemetría (solo diseño — sin código de captura)  
**Fuente de verdad:** [CONTEXT-healthcore.es.md](./CONTEXT-healthcore.es.md)  
**Catálogo de esquemas:** [event-schemas.json](./event-schemas.json)  
**Versión en inglés:** [telemetry-plan.md](./telemetry-plan.md)

Los identificadores `event_type` son **idénticos** a la versión en inglés (no se traducen).

---

## 1. Propósito y alcance

Operaciones y dirección presentaron un RFI: ¿puede el sistema de inventario en producción (y el resto de aplicaciones HealthCore que un usuario o proceso toque) generar información de negocio accionable? Este documento responde con un catálogo de diseño: qué capturar, por qué, y cómo debe viajar cada evento (batch vs stream), antes de instrumentar.

**Regla de oro:** si no se puede completar la frase, el evento no existe —

> Capturamos `[event_type]` porque necesitamos saber `[hipótesis]`, lo que nos permite tomar la decisión `[decisión concreta]`.

**En alcance**

- Métricas obligatorias de inventario del CONTEXT (piso P0).
- Catálogo ampliado de backoffice, website, jobs y salud de plataforma (techo P1/P2).
- Envelope, contratos JSON Schema, prioridad y modo de pipeline.

**Fuera de alcance (este hito)**

- Código de captura en FastAPI o Next.js.
- Pipeline de almacenamiento, dashboards o datos semilla del §5 del CONTEXT.
- Inventar PHI o campos ligados a pacientes.

---

## 2. Reglas regulatorias (HIPAA / UK GDPR)

Los eventos describen **insumos, existencias, operadores y resultados de proceso** — nunca pacientes.

| Permitido | Prohibido (incluso como dato de prueba) |
| --- | --- |
| `clinic_id`, `country` (`US`/`UK`), `department` / tipo de servicio | Nombre de paciente, historia clínica, diagnóstico |
| `userId` de staff (id TinyDB / UUID) | Cualquier identificador de paciente |
| SKU, categoría, cantidad, nombre de proveedor | Motivos en texto libre del formulario público |
| Id de incidencia, categoría, origen, códigos de estado | Narrativas que puedan incrustar PHI |

`department` es el **área clínica donde se consumió el insumo** (ej. `general_consultation`, `chronic_care`), no la unidad de RR.HH. del operador.

Website y talento pueden usar códigos (`clinic_id`, `country`, enums de etapa). No deben poner nombres, emails ni texto clínico en `properties`.

---

## 3. Mapeo de entidades y código

Los nombres del plan siguen el CONTEXT al pie de la letra. El código runtime usa los nombres de inventario HealthCore.

| Plan (CONTEXT) | Runtime hoy | Puntos de emisión principales |
| --- | --- | --- |
| `Product` | `MedicalSupply` (`medical_supplies`) | `POST /inventory/products`, list/get |
| `InboundOrder` | `SupplyDelivery` | `POST /inventory/orders/inbound` |
| `OutboundOrder` | `SupplyConsumption` | `POST /inventory/orders/outbound` |
| `clinic` | `clinic_id` (1–12, no FK) | Payloads de órdenes |
| `department` | **Aún no** en `SupplyConsumption` | Obligatorio en outbound al instrumentar |
| Stock | Calculado: entregas − consumos | Nunca una columna escribible |

### Mapeo `product_category` (vocabulario del evento ← código)

Enums de telemetría: `medication` | `ppe` | `consumable` | `equipment`.

| Código `MedicalSupply.category` | Evento `product_category` |
| --- | --- |
| `ppe` | `ppe` |
| `medications` | `medication` |
| `consumables` | `consumable` |
| `wound_care` | `consumable` |
| `diagnostics` | `consumable` |
| *(aún sin seed de equipment)* | `equipment` cuando se introduzca |

No inventar un tercer vocabulario. La traducción ocurre en el momento de emitir.

---

## 4. Event Envelope

Todo evento usa este sobre. Lo específico del evento vive en `properties`.

| Campo | Tipo | Propósito |
| --- | --- | --- |
| `eventId` | string (UUID) | Idempotencia y deduplicación |
| `timestamp` | string (ISO 8601 UTC) | Orden y ventanas temporales |
| `sessionId` | string \| null | Unir sesión UI con llamadas API |
| `userId` | string | Actor staff, o `system` / `job:*` para procesos automáticos |
| `event_type` | string | Taxonomía `entidad_acción` |
| `schemaVersion` | string (semver) | Evolucionar payloads sin romper consumidores |
| `requestId` | string \| null | Correlacionar frontend → FastAPI → logs |
| `properties` | object | Payload específico |

**Campos mínimos de inventario en `properties`** (CONTEXT): `clinic_id`, `country`, `product_id`, `product_category`, `quantity`, y `department` solo cuando aplique.

Contratos completos: [event-schemas.json](./event-schemas.json).

---

## 5. Batch vs stream

| Modo | Necesidad de negocio | Uso típico |
| --- | --- | --- |
| **Stream** | Enterarse en segundos | Alertas de stock, rechazos de control, anomalías de auth, 5xx |
| **Batch** | Bastan agregados periódicos | Totales de compra, ritmos de consumo, barridos de vencimiento, logins/día |

Regla práctica: si Marcus o Claire avisarían a alguien a las 14:00 → stream; si la Dra. Okonkwo necesita un gráfico el lunes → batch (opcionalmente sobre stream).

---

## 6. P0 — Métricas obligatorias (piso del CONTEXT)

Estas cinco deben instrumentarse de punta a punta al final de la serie de proyectos de telemetría. Se diseñan para agregarse por clínica y país.

### 6.1 `inbound_order_created`

| | |
| --- | --- |
| **Se dispara cuando** | Una clínica registra la recepción de insumos de un proveedor |
| **Regla de oro** | Capturamos `inbound_order_created` porque necesitamos saber cuánto y qué insumo se compra por clínica y proveedor, lo que permite consolidar compras y negociar mejores condiciones |
| **Emisión** | Tras `POST /inventory/orders/inbound` exitoso (`create_delivery`) |
| **Modo** | Batch |
| **Properties extra** | `vendor_name`, `sku`, `unit`, `order_id` |

### 6.2 `outbound_order_created`

| | |
| --- | --- |
| **Se dispara cuando** | Una clínica registra el consumo de un insumo en la atención de un departamento |
| **Regla de oro** | Capturamos `outbound_order_created` porque necesitamos saber qué insumos se consumen más y a qué ritmo por clínica y departamento, lo que permite ajustar la reposición automática de insumos críticos |
| **Emisión** | Tras `POST /inventory/orders/outbound` exitoso (`create_consumption`) |
| **Modo** | Batch |
| **Properties extra** | `department` (obligatorio), `consumption_type` (`clinical_use` \| `expiry_waste`), `sku`, `order_id` |

Responde: “¿Cuántas órdenes de salida se registran por día?”

### 6.3 `stock_threshold_triggered`

| | |
| --- | --- |
| **Se dispara cuando** | El stock de un insumo en una clínica cae por debajo del mínimo configurado |
| **Regla de oro** | Capturamos `stock_threshold_triggered` porque necesitamos saber con qué frecuencia una clínica se queda corta de un insumo crítico, lo que permite priorizar reabastecimiento urgente y escalar a Marcus (Operaciones Clínicas) |
| **Emisión** | Tras outbound (y opcionalmente tras recalcular inbound) si `current_stock < min_stock`; job diario de reconciliación opcional |
| **Modo** | Stream |
| **Properties extra** | `current_stock`, `min_stock_threshold`, `threshold_band` (`low` \| `critical`) |

La UI hoy usa bandas crítico &lt; 5 y bajo &lt; 15. Estado objetivo: `min_stock` configurable por producto/clínica.

### 6.4 `direct_stock_edit_rejected`

| | |
| --- | --- |
| **Se dispara cuando** | Un usuario intenta modificar el stock directamente (fuera de una orden) y el sistema lo rechaza |
| **Regla de oro** | Capturamos `direct_stock_edit_rejected` porque necesitamos saber si el personal intenta saltarse el control de trazabilidad, lo que permite reforzar capacitación o permisos en la clínica donde más ocurre |
| **Emisión** | Rutas de rechazo explícitas: `PUT`/`PATCH` de stock, `current_stock` prohibido en create/update, middleware en mutaciones de inventario fuera de órdenes → 403/405 + evento |
| **Modo** | Stream |
| **Properties extra** | `attempted_path`, `http_status`, `rejection_reason` (`direct_stock_mutation_forbidden`); `department` no aplica |

**No es este evento:** outbound `400 Insufficient stock` (eso es `outbound_order_rejected` en P1).

### 6.5 `supply_expiry_flagged`

| | |
| --- | --- |
| **Se dispara cuando** | Un lote de insumo se acerca a su fecha de vencimiento (ej. 30 días) |
| **Regla de oro** | Capturamos `supply_expiry_flagged` porque necesitamos saber qué insumos están por vencer antes de volverse merma o riesgo de cumplimiento, lo que permite priorizar uso o baja controlada del lote |
| **Emisión** | Job programado (diario) leyendo `Product.expiry_date` |
| **Modo** | Batch |
| **Properties extra** | `expiry_date`, `days_to_expiry`, `batch_id` (cuando existan lotes); `department` no aplica; `quantity` = stock restante del producto/clínica |

El CONTEXT exige la fecha de vencimiento en el modelo `Product` para cálculo consistente entre clínicas.

---

## 7. Huecos de instrumentación (estado objetivo)

Documentados para que quien implemente sepa qué falta en runtime. Este plan describe el objetivo; no cambia código.

| Hueco | Impacto | Objetivo |
| --- | --- | --- |
| Sin `expiry_date` en `MedicalSupply` | `supply_expiry_flagged` no computable | Añadir `expiry_date` en `Product` |
| Sin `min_stock` en API | Umbrales son números mágicos de UI | Persistir mínimo por producto/clínica |
| Sin `department` en `SupplyConsumption` | Properties CONTEXT de outbound incompletas | Exigir `department` en create outbound |
| Sin endpoint de escritura de stock | Rechazos silenciosos (405 / extras ignorados) | Rechazo explícito + emitir `direct_stock_edit_rejected` |
| Maestro de clínicas | Agregación por región incompleta | TODO: registro formal de clínicas |

---

## 8. Mapa de superficies de la aplicación

Cualquier toque humano o de proceso es oportunidad de dato. El inventario es el piso; el resto evita un plan “solo mínimo”.

| Zona | Superficies | Actor |
| --- | --- | --- |
| A Inventario | Lista de productos, formularios inbound/outbound, historial | Staff |
| B Auth y cuenta | Login, registro, logout, forgot/reset/change password, perfil | Staff |
| C Incidencias | Listar/filtrar, crear, status, summary, CSV analyze/export | Staff |
| D Proveedores | Crear, listar/filtrar, tarifa, estado, borrar | Staff |
| E People & Talent | `/applications`, `/candidates/[id]` | Staff (PII laboral, no PHI) |
| F Placeholders | Patients, Appointments, Billing, Claims, Reports | Staff (solo page views hasta que existan) |
| G Website | Home, intake `/application` (submit demo) | Público |
| H Jobs / internos | Seeds, Resend, futuro barrido de vencimientos | `system` / `job:*` |
| I Plataforma | HTTP 4xx/5xx, validación, latencia | Plataforma |

---

## 9. Catálogo ampliado (P1 / P2)

Cada fila cumple la regla de oro. Identificadores alineados con [event-schemas.json](./event-schemas.json).

### 9.1 Extras de inventario (P1)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `product_created` | Crecimiento del catálogo y mezcla de categorías → cobertura de stock | Batch | `POST /inventory/products` 201 |
| `outbound_order_rejected` | Fallos de validación/stock por producto → UX y formación | Batch | Outbound 400 |
| `inbound_order_rejected` | Payloads inbound inválidos → formularios / calidad de vendor | Batch | Inbound 400/422 |
| `inventory_form_started` | Qué flujos de inventario se abren → priorizar UX | Batch | Montaje del formulario |
| `inventory_form_abandoned` | Abandono a mitad → simplificar formularios | Batch | Inicio sin submit en la ventana de sesión |

### 9.2 Auth (P1 — preguntas del tech lead)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `login_succeeded` | Volumen de acceso exitoso → capacidad y turnos | Batch | `POST /auth/login` 200 |
| `login_failed` | Intentos fallidos por día → fuerza bruta / UX | Stream | `POST /auth/login` 401 |
| `logout_completed` | Cierres de sesión → higiene de sesiones | Batch | Clear session en cliente |
| `user_registered` | Altas de cuentas backoffice → gobierno de acceso | Batch | `POST /users` 201 |
| `password_reset_requested` | Demanda de reset (sin enumerar email en props) → carga de soporte | Batch | `POST /auth/forgot-password` |
| `password_reset_completed` | Tasa de completado → fricción de token/email | Batch | `POST /auth/reset-password` 200 |
| `password_reset_failed` | Tokens inválidos/caducados → TTL y mensajes | Stream | Reset 400 |
| `password_changed` | Cambios autenticados → pista de auditoría | Batch | `POST /auth/change-password` 200 |
| `session_unauthorized` | Tokens ausentes/caducados → UX de sesión | Stream | 401 en rutas protegidas |

Auth `properties`: nunca password ni token de reset. Preferir `userId` opaco o email hasheado.

### 9.3 Navegación UX (P1)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `page_viewed` | Secciones más visitadas (incl. placeholders) → roadmap | Batch | Cambio de ruta |
| `form_abandoned` | Flujos abandonados a mitad → reducir fricción | Batch | Formulario iniciado sin submit |

`page_viewed.properties`: `path`, `app` (`backoffice` \| `website`), `referrer_path` opcional. Sin PHI.

### 9.4 Incidencias (P1)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `incident_created` | Volumen por origen/sede/categoría → staffing ops | Batch | `POST /api/incidents` 201 |
| `incident_validation_failed` | Campos que más fallan → UX de validación | Batch | Create 400 |
| `incident_status_changed` | Throughput del ciclo de vida → SLA | Batch | `PATCH .../status` 200 |
| `incident_status_rejected` | Transiciones ilegales → formación / guards UI | Batch | Transición ilegal 400 |
| `incident_csv_analyzed` | Uso del análisis → invertir en tooling CSV | Batch | Analyze 200 |
| `incident_csv_rejected` | Uploads malformados → plantillas/docs | Batch | Analyze 400 |
| `incident_results_exported` | Demanda de export → retención de results.csv | Batch | Export 200 |
| `incident_summary_viewed` | Uso del resumen → mantener el dashboard útil | Batch | Summary / GET summary |

Properties: ids, status, category, origin, branch — no texto libre con PHI.

### 9.5 Proveedores (P1)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `supplier_created` | Crecimiento del directorio → cobertura de compras | Batch | `POST /suppliers` 201 |
| `supplier_rate_updated` | Cambios de tarifa → negociación con datos inbound | Batch | `PATCH .../rate` |
| `supplier_status_changed` | Activaciones/suspensiones → riesgo de vendor | Batch | `PATCH .../status` |
| `supplier_deleted` | Bajas → higiene del directorio | Batch | `DELETE /suppliers/{id}` |

Se relaciona con `inbound_order_created.vendor_name` para consolidar compras.

### 9.6 People & Talent (P2)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `talent_list_filtered` | Patrones de filtro de reclutadores → UX de hiring | Batch | Filtros en applications |
| `talent_record_created` | Volumen de entrada al pipeline → KPIs de Diane | Batch | Crear registro |
| `talent_candidate_viewed` | Atención por candidato → cuellos de botella | Batch | Abrir `/candidates/[id]` |

PII laboral: solo ids y enums de stage/status — sin texto de CV ni documentos de identidad en eventos.

### 9.7 Website público (P2)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `website_page_viewed` | Tráfico home vs intake → inversión en acceso paciente | Batch | Vista de ruta |
| `intake_form_started` | Cuántos inician intake → embudo | Batch | Montaje/foco del form |
| `intake_form_submitted` | Volumen de submit por país/clínica (códigos) → demanda de acceso | Batch | Submit ok (solo códigos) |
| `intake_form_validation_failed` | Campos que bloquean → UX del form | Batch | Fallo de validación cliente |

**Prohibido en properties:** `fullName`, `email`, `phone`, `reason` u otras narrativas de paciente.

### 9.8 Plataforma / jobs (P1–P2)

| `event_type` | Hipótesis → decisión | Modo | Emisión |
| --- | --- | --- | --- |
| `http_request_failed` | Tasas 4xx/5xx por ruta → fiabilidad antes de que llame la clínica | Stream (5xx) / Batch (agregados 4xx) | Middleware de respuesta |
| `api_unhandled_error` | 500 inesperados → avisar on-call | Stream | Handler de excepción no controlada |
| `email_send_failed` | Fallos de Resend sin filtrar direcciones → arreglar email | Stream | Fallo al enviar reset |
| `job_run_completed` | Salud de seeds/barridos → confianza ops | Batch | Fin de job (`job_name`, `status`, `duration_ms`) |

---

## 10. Prioridad y boceto de pipeline

| Prioridad | Eventos | Pipeline |
| --- | --- | --- |
| **P0** | Cinco tipos obligatorios del CONTEXT | Stream: `stock_threshold_triggered`, `direct_stock_edit_rejected`. Batch: inbound/outbound created, `supply_expiry_flagged` |
| **P1** | Auth, UX, extras inventario, incidencias, proveedores, errores de plataforma | Stream seguridad/5xx; batch agregados |
| **P2** | Talento, embudo website | Batch |

```text
[Backoffice | Website | Jobs]
          │
          ▼
   Event envelope (+ schemaVersion)
          │
     ┌────┴────┐
     ▼         ▼
  Stream     Batch
  (alertas,  (rollups horarios/diarios
   seguridad) → dashboards)
```

**Correlación:** generar `requestId` en cliente (o gateway), pasar como header (ej. `X-Request-Id`), reflejarlo en logs API y telemetría.

**Política `schemaVersion`:** empezar en `1.0.0`. Campos opcionales aditivos → minor. Rename/remove → major con ventana de doble lectura.

---

## 11. TODOs abiertos

- TODO: Confirmar maestro formal de las 12 clínicas (`clinic_id`, país, estado/región) para agregación ejecutiva.
- TODO: Confirmar horario del barrido de vencimientos (asunción: diario 06:00 UTC, ventana 30 días).
- TODO: Confirmar si la categoría `equipment` aparece en seed antes del hito de captura.
- TODO: Los volúmenes de seed del §5 del CONTEXT son para un hito posterior — no se generan en este pase de diseño.

---

## 12. Notas de entrega

- Cambio solo de documentación; no se ejecutaron tests automatizados.
- Los `event_type` obligatorios y el piso de properties de inventario coinciden con [CONTEXT-healthcore.es.md](./CONTEXT-healthcore.es.md).
- La versión en inglés usa los mismos identificadores: [telemetry-plan.md](./telemetry-plan.md).
