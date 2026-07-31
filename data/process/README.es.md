# `data/process` — artefactos procesados / generados

Esta carpeta guarda **salidas** derivadas de datos raw o pipelines: agregados, tablas limpias y exportaciones de análisis.

Línea clara: `data/raw/` = entradas originales; `data/process/` = lo que generamos.

## Propósito

- Separar datasets fuente de artefactos regenerables.
- Dar a exporters y pipelines un lugar estable para escribir resultados.
- Evitar versionar archivos generados ruidosos cuando se pueden reproducir en local.

## Artefactos actuales

| Archivo | Lo produce | Qué es |
| --- | --- | --- |
| `results.csv` | `scripts/analyze.py` → `services.incidents_analysis.exporter` | Resumen de métricas (`metric`, `value`, `percentage`). Sin `patient_id`. Se regenera si el usuario responde `y` al prompt de exportación. |

## Consejos

- Prefiere regenerar `results.csv` en lugar de editarlo a mano.
- No guardes aquí exportaciones con PHI/PII.
- CSVs generados como `results.csv` van en `.gitignore` cuando son reproducibles desde `data/raw/`.
