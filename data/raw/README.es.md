# 📦 `data/raw` — zona de aterrizaje de datos originales

Esta carpeta guarda datasets de la compañía **sin transformar**: dumps, exports y archivos de muestra que scripts o servicios consumen tal cual.

Piensa en ella como el muelle de carga: los datos llegan aquí antes de limpiarse, validarse o agregarse.

## Propósito

- Separar con claridad la entrada **raw** de las salidas procesadas (`data/process/`).
- Dar a scripts y servicios un lugar estable para localizar archivos fuente / de prueba.
- Documentar origen, formato y restricciones de privacidad de cada dataset.

## 📂 Datasets actuales

| Archivo | Qué es | Notas |
| --- | --- | --- |
| `incidents-healthcore.csv` | Muestra de reportes de incidentes de pacientes (HealthCore) | UTF-8, separador coma, fila de encabezado. Lo usa `scripts/analyze.py` a través de `services/incidents-analysis`. |

### 🔒 Privacidad (no negociable)

`incidents-healthcore.csv` incluye valores de `patient_id` protegidos por **HIPAA** (EE. UU.) y **UK GDPR** (Reino Unido).

- **No** envíes este archivo a herramientas de IA externas.
- El código aguas abajo no debe imprimir, registrar ni exportar valores de `patient_id`.
- Reglas de negocio y métricas esperadas: `docs/data-contract/CONTEXT-HealthCore.es.md`.

## 💡 Consejos

- Prefiere muestras sintéticas o desidentificadas en git cuando sea posible.
- Documenta cada archivo nuevo: origen, esquema, tamaño aproximado y riesgo PII/PHI.
- No guardes aquí salidas de pipelines — eso va en `data/process/`.
