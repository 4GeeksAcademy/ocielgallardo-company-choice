# 🚀 `scripts` — entrypoints ligeros y tooling del equipo

Esta carpeta agrupa **puntos de entrada CLI** y scripts auxiliares del monorepo: runners de análisis, helpers de setup y otras herramientas fáciles de lanzar desde la raíz del repo.

Regla práctica: los scripts **coordinan**; la lógica reutilizable vive en otro sitio (por ejemplo bajo `services/`).

## Propósito

- Ofrecer un comando simple sin tener que conocer el interior del paquete.
- Evitar meter reglas de negocio en un script suelto, para que la misma lógica pueda alimentar una API más adelante.
- Documentar cómo ejecutar cada script con seguridad (sobre todo si hay PHI/PII).

## 📁 Scripts en esta carpeta

### `analyze.py` — análisis de reportes de incidentes (CLI)

Coordina el flujo completo del análisis CSV de incidentes de HealthCore. **No** contiene las reglas de negocio; delega en `services/incidents_analysis`.

```text
analyze.py
    |
    +-- csv_reader   -> leer el CSV
    +-- validator    -> reglas valido / invalido
    +-- analyzer     -> metricas agregadas
    +-- consola      -> imprimir el informe
    +-- exporter     -> CSV de metricas opcional (tras prompt y/n)
```

**Uso típico** (desde la raíz del repo; la ruta puede variar según el entorno):

```bash
python scripts/analyze.py data/raw/incidents-healthcore.csv
```

**Fuente de verdad**

- Requisitos: `docs/data-contract/CONTEXT-HealthCore.es.md`
- Flujo funcional: `docs/data-contract/functional-design-analyze.es.md`
- Módulos reutilizables: `services/incidents_analysis/`
- Exportación (opcional): `data/process/results.csv`

🛡 **Recordatorio de cumplimiento:** nunca imprimas ni exportes `patient_id`. Si el script muestra un identificador de paciente, la salida no es usable.

## 💡 Consejos

- Mantén cada script enfocado: parsear args, llamar servicios, mostrar resultados.
- Prefiere importar desde `services/` en lugar de copiar lógica al script.
- Documenta parámetros, entradas esperadas y efectos secundarios (archivos escritos, prompts interactivos).
