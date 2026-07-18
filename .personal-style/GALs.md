# GALs del Proyecto

Este documento define la ejecución lineal del proyecto en fases GAL.

GAL = Goal, Actions, Learnings

En todos los GALs aplica la misma regla: seguir siempre las reglas de diseño y marca de HealthCore.

Fuentes obligatorias:

1. `.agents/rules/design.md`
2. `stitch_healthcore_design_system/healthcore_design_system_design.md`
3. `stitch_healthcore_design_system/clinical_intelligence_system/DESIGN.md`

## GAL 1 - Inventario visual por sección

Goal:

Definir qué tipo de imagen tendrá cada sección principal.

Actions:

1. Hero: definir imagen principal (humana, clínica, confiable).
2. Services: definir soporte visual por card (icono, mini visual o foto recortada).
3. Impact: definir recurso visual orientado a datos.
4. CTA: definir imagen de cierre con tono de acompañamiento.
5. Definir ubicación y nombres de assets.

Learnings esperados:

1. Qué tipo de imagen aporta más claridad por sección.
2. Qué tipo de imagen se debe evitar para no romper el tono.

Entregables:

1. Tabla sección -> tipo de imagen -> intención -> formato.
2. Lista de assets objetivo.

Criterio de salida:

Inventario visual aprobado.

## GAL 2 - Contrato de animación

Goal:

Definir animaciones exactas antes de implementar.

Actions:

1. Establecer animación de entrada por sección.
2. Establecer animación de hover por componente clave.
3. Establecer animaciones por scroll en bloques de contenido.
4. Definir duración, delay y easing por tipo de animación.
5. Definir trigger (load, hover, in-view).

Learnings esperados:

1. Nivel óptimo de movimiento sin ruido.
2. Dónde el motion aporta realmente valor.

Entregables:

1. Matriz sección -> animación -> trigger -> duración -> intensidad.

Criterio de salida:

Contrato de animación aprobado.

## GAL 3 - Límites técnicos y accesibilidad

Goal:

Proteger rendimiento y legibilidad antes de mover la UI.

Actions:

1. Definir peso máximo por imagen y por sección.
2. Definir número máximo de animaciones simultáneas.
3. Definir fallback para `prefers-reduced-motion`.
4. Definir reglas de lazy loading y prioridad visual.
5. Definir checklist mínimo de accesibilidad visual.

Learnings esperados:

1. Equilibrio entre impacto visual y performance.

Entregables:

1. Reglas técnicas de imágenes y motion.
2. Lista de verificación de accesibilidad y rendimiento.

Criterio de salida:

Límites técnicos documentados y aprobados.

## GAL 4 - Vertical slice Hero

Goal:

Implementar una referencia real en Hero para validar estilo final.

Actions:

1. Integrar imagen principal del Hero.
2. Integrar una animación de entrada de bloque.
3. Integrar microinteracción principal en CTA.
4. Ajustar responsive y jerarquía visual.

Learnings esperados:

1. Qué tan bien conviven imagen + motion con la base actual.

Entregables:

1. Hero funcionando como patrón.

Criterio de salida:

Hero aprobado para replicar patrón.

## GAL 5 - Escalar patrón en Services

Goal:

Aplicar el patrón validado a la sección de servicios.

Actions:

1. Integrar soporte visual por card.
2. Aplicar aparición escalonada (stagger) sutil.
3. Mejorar hover con retroalimentación visual ligera.

Learnings esperados:

1. Densidad visual correcta para grids de cards.

Entregables:

1. Sección Services con mayor dinamismo y coherencia.

Criterio de salida:

Sección clara, legible y consistente con marca.

## GAL 6 - Escalar patrón en Impact

Goal:

Mejorar lectura de datos con recursos visuales y motion controlado.

Actions:

1. Integrar recurso visual secundario en bloque de impacto.
2. Aplicar animación de aparición en KPIs.
3. Ajustar jerarquía de lectura para datos.

Learnings esperados:

1. Qué motion mejora comprensión de métricas.

Entregables:

1. Sección Impact más expresiva sin perder claridad.

Criterio de salida:

Métricas legibles y visualmente más vivas.

## GAL 7 - Escalar patrón en CTA final

Goal:

Fortalecer el cierre de la página con apoyo visual y mejor foco de acción.

Actions:

1. Integrar imagen secundaria de apoyo.
2. Aplicar animación suave de aparición.
3. Reforzar protagonismo del botón principal.

Learnings esperados:

1. Qué combinación mejora intención de clic sin saturación.

Entregables:

1. CTA final más sólido y coherente.

Criterio de salida:

Cierre visual consistente y accionable.

## GAL 8 - Cierre de calidad y continuidad

Goal:

Cerrar implementación y dejar el proyecto listo para nuevas sesiones.

Actions:

1. Revisar consistencia visual completa.
2. Revisar experiencia en móvil y desktop.
3. Validar accesibilidad visual y de movimiento.
4. Validar rendimiento general.
5. Registrar resultados y pendientes en `contexts.md`.

Learnings esperados:

1. Qué ajustes finales sostienen calidad a futuro.

Entregables:

1. Checklist final completo.
2. Documentación final del estado del proyecto.

Criterio de salida:

Proyecto documentado, consistente y listo para siguientes iteraciones.
