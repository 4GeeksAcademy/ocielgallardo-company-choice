# Design System: HealthCore

**Proyecto:** Unidad interna de transformación digital - 4Geeks Academy
**Versión:** 1.0 (Basado en Milestone 1 & 2)
**Estado:** Documentación Maestra

## 1. Identidad de Marca (Brand Identity)

HealthCore no es solo un software; es el puente entre la eficiencia operativa y el cuidado humano.

- **Personalidad:** Confiable, clínica, humana, moderna y segura.
- **Tono de Voz:** Claro, empático y profesional. Evitamos la jerga médica excesiva para priorizar la comprensión del paciente y la agilidad del staff.
- **Concepto de Logo:** Icono circular que integra una cruz médica estilizada con un globo terráqueo, simbolizando su red internacional (USA/UK).
- **Tagline:** "Atención médica inteligente, segura y humana."

---

## 2. Sistema de Color (Color System)

El sistema utiliza una base de azules clínicos profesionales extendida con colores semánticos para el análisis de riesgo predictivo.

### Colores Principales

| Token | HEX | Uso Principal |
| :--- | :--- | :--- |
| `primary-600` | `#2563eb` | Botones primarios, iconos activos, branding. |
| `primary-700` | `#1d4ed8` | Estados hover, acentos fuertes. |
| `primary-900` | `#1e3a8a` | Headers, texto hero, fondos oscuros de marca. |

### Colores Neutrales (Escala Slate)

| Token | HEX | Uso Principal |
| :--- | :--- | :--- |
| `slate-50` | `#f8fafc` | Fondos de página, áreas de trabajo limpias. |
| `slate-200` | `#e2e8f0` | Bordes de cards, dividers, inputs deshabilitados. |
| `slate-600` | `#475569` | Texto secundario, etiquetas de formulario. |
| `slate-800` | `#1e293b` | Texto de cuerpo principal, headings secundarios. |
| `slate-950` | `#020617` | Headings de alto contraste, modo oscuro. |

### Colores Semánticos y Niveles de Riesgo

| Estado / Riesgo | HEX / Tailwind | Uso |
| :--- | :--- | :--- |
| `Success` | `green-500` | Confirmaciones, citas asistidas, facturas pagadas. |
| `Warning` | `amber-500` | Riesgo bajo-medio, recordatorios pendientes. |
| `Danger / Critical`| `red-600` | Alertas críticas, no-shows, facturas rechazadas. |
| `Info` | `cyan-500` | Información de sistema, ayuda, tips. |

**Accesibilidad:** Contraste mínimo WCAG AA (4.5:1) garantizado para todo el texto legible sobre fondos.

---

## 3. Tipografía (Typography)

Priorizamos la legibilidad en contextos de alta densidad de datos (Dashboards).

- **Fuente:** `Inter` (Sans-serif).
- **Escala de Texto:**
    - `h1`: 3xl a 5xl (Extrabold) - Títulos de Hero y landing.
    - `h2`: 2xl a 3xl (Bold) - Títulos de sección y KPIs grandes.
    - `h3`: xl (Semibold) - Títulos de cards y widgets.
    - `body`: base (Regular) - Texto principal.
    - `caption`: sm/xs (Medium) - Metadatos, etiquetas de tablas, notas legales.
- **Line-height:** 1.5 para cuerpo de texto para reducir la fatiga visual.

---

## 4. Espaciado y Layout (Spacing & Layout)

- **Contenedores:**
    - `max-w-7xl`: Para landing pública y dashboards.
    - `max-w-5xl`: Para formularios de registro (mejora el foco).
- **Grid System:** 1 columna en mobile → 2 columnas en tablet → 3-5 columnas en desktop (dashboard).
- **Padding:** Secciones estándar `py-14`, contenedores laterales `px-4 sm:px-6 lg:px-8`.
- **Border Radius:**
    - `lg (8px)`: Elementos pequeños (botones).
    - `xl (12px)`: Cards estándar.
    - `2xl (16px)`: Secciones de landing y contenedores grandes.
    - `full`: Badges, avatares y pills.

---

## 5. Biblioteca de Componentes (Components Library)

### Navegación y Estructura
- **Header:** Sticky, fondo glass (blur), nav links y CTA "Registro" (`blue-600`).
- **Footer:** 4 columnas (Marca, Servicios, Legal, Sedes), fondo `slate-950` para contraste.

### Cards y Visualización
- **Service Cards:** Fondo blanco, `rounded-2xl`, sombra suave, hover con elevación (`-translate-y-1`).
- **KPI Widgets:** Valor numérico grande (`text-3xl`), etiqueta debajo, indicador de tendencia/riesgo a la derecha.
- **Probability Bars:**
    ```text
    [||||||||-- 82% --] (Color: Red-600 si > 70%)
    ```

### Formularios
- **Inputs:** `border-slate-200`, `focus:ring-2`, `focus:ring-blue-600`.
- **Validation:** Mensajes de error en `red-600` con `aria-live="polite"`.

---

## 6. Plantillas de Página (Page Templates)

### A) Landing Pública (Vigente)
1. **Hero:** Gradiente `blue-900` a `blue-700` con glass card para el mensaje central.
2. **Servicios:** Grid de 3x2 con iconos de especialidades.
3. **Estadísticas:** Sección de impacto (12 clínicas, 200+ profesionales).
4. **Flujo Paciente:** Diagrama visual de 4 pasos (Reserva → Validación → Atención → Seguimiento).

### B) Formulario de Registro (Vigente)
- Estructura lineal por fieldsets: Datos Personales → Ubicación → Clínica/Motivo → Consentimiento Legal.

### C) Dashboard Operacional (Futuro)
- **Vista Priya Nair (Patient Experience):**
    - Top: KPI de No-Show Rate actual (vs 22% baseline).
    - Centro: Lista de "Próximas citas con alto riesgo de No-Show".
    - Acciones: Botón rápido de "Enviar Recordatorio WhatsApp/SMS".
- **Vista Tom Callahan (Revenue Cycle):**
    - Centro: "Facturas con probabilidad de rechazo > 60%".
    - Alertas: CriticalAlerts por errores de codificación detectados por IA.

---

## 7. Iconografía e Imágenes

- **Estilo de Iconos:** Lineal, 2px de grosor (estilo Lucide/Heroicons).
- **Imágenes:** Fotografía médica real, diversa y optimista. Evitamos el stock genérico sobre-expuesto.
- **Regla:** Nunca usar imágenes de agujas, sangre o pacientes sufriendo en interfaces operativas.

---

## 8. Accesibilidad y Cumplimiento (Compliance)

- **Foco:** Anillos de foco visibles siempre (`ring-offset-2`).
- **Navegación:** Enlaces de "Saltar al contenido" presentes.
- **Privacidad:** Los dashboards internos deben anonimizar PHI (Protected Health Information) a menos que el rol tenga permisos específicos. Consentimiento HIPAA/GDPR explícito en el footer de cada formulario.

---

## 9. Brand Do's & Don'ts

| Do's | Don'ts |
| :--- | :--- |
| Usar azules para transmitir calma y seguridad. | No usar sombras duras o colores neón. |
| Mantener el tono profesional y empático. | No usar jerga técnica que confunda al paciente. |
| Priorizar la acción principal (CTA). | No saturar la UI con demasiados KPI secundarios. |
| Asegurar el contraste WCAG AA. | No usar el color rojo para estados que no sean críticos. |

---

## 10. Mapeo de Entidades (Domain Mapping)

| Entidad | Componente UI Sugerido |
| :--- | :--- |
| `Appointment` | Card en lista o fila de tabla con probabilidad. |
| `Invoice` | Fila de tabla con badge de estado (Rejected/Paid). |
| `NoShowPrediction`| Indicador visual de riesgo (Low/Medium/High). |
| `CriticalAlert` | Banner superior o card con borde `red-600`. |

---
**Generado por Stitch para el equipo de HealthCore.**
"Atención médica inteligente, segura y humana."
