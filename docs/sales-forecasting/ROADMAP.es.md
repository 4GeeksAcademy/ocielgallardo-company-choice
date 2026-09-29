# Checklist — Modelo de predicción de ventas (HealthCore)

> Fuente de negocio: `CONTEXT-healthcore.es.md` / `CONTEXT-healthcore.en.md` (misma carpeta).
> Ticket del tech lead: split honesto 8/2 años, visualización con rango de variabilidad,
> justificación XGBoost vs Random Forest, métrica explicable para Finanzas.

## Fase 1 — Preparación de datos

### 1.0 Fuente y estado verificado del dataset

- [x] Confirmar archivo canónico: `data/raw/healthcore_sales.csv`
- [x] Verificar 120 filas `region == "consolidated"`, rango `2016-01-01` → `2025-12-01`
- [x] Verificar columnas: `month`, `revenue_usd` (target), `visits_count`, `avg_revenue_per_visit_usd`, `region`
- [x] Chequeo de calidad ejecutado (0 celdas vacías, 0 tokens `null`/`NaN`, 0 parseos fallidos, 0 `revenue_usd <= 0`, 0 meses faltantes)
- [x] Dejar constancia del chequeo en el log del script de preparación (`scripts/prepare_sales_data.py`)

### 1.1 Tratamiento de nulos y vacíos

- [x] Normalizar celdas en blanco y tokens (`""`, `"null"`, `"NaN"`, `"N/A"`, `"?"`) a `NaN` real
- [x] Validar tipos: `month` → fecha `YYYY-MM-01`; numéricas → float/int; `region == "consolidated"`
- [x] Aplicar restricciones del CONTEXT: `revenue_usd > 0`, rango 2016-01…2025-12 continuo
- [x] Ante cualquier `NaN` → error explícito con fila y columna (sin imputación silenciosa)
- [x] Solo como fallback documentado: imputación causal `ffill` (únicamente datos pasados, jamás futuros)
- [x] Reportar conteos pre/post limpieza

### 1.2 División 8 años train / 2 años test (sin fuga)

- [x] Corte cronológico estricto sin shuffle: train 96 meses (`2016-01` → `2023-12`), test 24 meses (`2024-01` → `2025-12`)
- [x] Ejecutar el split **antes** de calcular features o estadísticas
- [x] Features calendario (`year`, `month_sin/cos`) derivadas de forma **causal** (el mes se conoce de antemano, sin fuga)
- [ ] Lags/rolling (`lag_1/3/6/12`, `rolling_mean_3/12`) → diferidos a Fase 2, con regla causal (solo filas pasadas)
- [ ] Historia de test tomada del final de train, sin exponer targets futuros (aplica desde Fase 2)
- [x] Aserciones: `max(month_train) < min(month_test)`, conteos 96/24 exactos, intersección vacía
- [x] Prueba unitaria `tests/pipelines/test_sales_split.py` en verde

### 1.3 Escalado de variables

- [x] `StandardScaler`: `fit` solo en train, `transform` en train y test con esos parámetros
- [x] Persistir el scaler (p. ej. `joblib`) con parámetros de train para inferencia
- [x] Escalar numéricas base (`visits_count`, `avg_revenue_per_visit_usd`)
- [x] Derivar `month` a `year` + cíclicas `month_sin`/`month_cos` (no escalar fecha directa)
- [x] Documentar en el informe: RF/XGBoost son invariantes a escala; el escalado se aplica por requisito y para un posible baseline lineal

> Nota de implementación (2026-09-29): escalado z-score con la misma matemática que
> `StandardScaler` pero sin dependencia sklearn (el env `uv` aún no la trae; llegará
> con el modelo cuando el equipo lo defina). Parámetros persistidos en
> `data/process/sales_forecasting/scaler.json` (gitignored). Artefactos:
> `train_scaled.csv` (96) + `test_scaled.csv` (24).

### 1.4 Cierre de la Fase 1

- [x] `uv run python -m pytest tests/pipelines/test_sales_split.py -q` → passed
- [x] `git diff --check` limpio
- [x] Artefactos listos: dataset limpio validado + scaler persistido
