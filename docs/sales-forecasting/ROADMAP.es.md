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

---

## Fase 2 — Entrenamiento

### 2.0 Decisión: Random Forest (decidido por el equipo, 2026-09-29)

- [x] Modelo elegido: **Random Forest** (`scikit-learn`, `random_state` fijo)
- [x] Descartado: XGBoost (ver porqué abajo)

**Porqué (del análisis previo a la decisión):**

1. **Pocos datos mandan (96 filas de train).** El riesgo dominante es la varianza — memorizar el pasado,
   justo lo que el ticket prohíbe. RF la reduce por construcción (promedio de árboles independientes);
   XGBoost solo la controla con regularización bien calibrada, difícil de validar con tan poco train.
2. **Señal simple.** Tendencia + estacionalidad anual marcada no necesitan la expresividad del boosting.
3. **Banda de variabilidad nativa.** Percentiles entre árboles (p10–p90) sin maquinaria extra;
   XGBoost exigiría objetivo cuantil o bootstrap externo.
4. **Relato explicable a Finanzas.** "Promediamos N árboles independientes" + importancia de variables;
   sin tasa de aprendizaje ni rondas de boosting que justificar.
5. **Menor costo operativo.** Solo `scikit-learn`, sin librería nativa pesada en Windows ni en la imagen Docker `slim`.
   La ventaja de escala de XGBoost (datos masivos distribuidos) no se materializa con 12 filas/año.

### 2.1 Dónde se entrena

- [x] Entrenamiento local con `uv` (script standalone, segundos en CPU, sin GPU)
- [x] Dependencias añadidas al proyecto: `scikit-learn`, `matplotlib` (visualización)
- [x] Artefactos del modelo gitignored en `data/process/sales_forecasting/` (igual que Fase 1)

### 2.2 Features (causales, sin fuga)

- [x] Lags `lag_1/3/6/12` y `rolling_mean_3/12` calculados solo con filas pasadas (`scripts/train_sales_model.py::add_lag_features`)
- [x] Base Fase 1: `visits_count`, `avg_revenue_per_visit_usd` (escaladas), `year`, `month_sin/cos`
- [x] Historia de test tomada del final de train, sin exponer targets futuros (warm-up de 12 meses cae dentro de train → 84/24)

### 2.3 Entrenamiento y evaluación honesta

- [x] `RandomForestRegressor` entrenado **solo** en train (2017–2023 efectivos, 84 filas, `random_state=42`)
- [x] Predicción + banda p10–p90 sobre test (2024–2025, 24 meses jamás vistos)
- [x] Métrica principal para Finanzas: **RMSE como % del ingreso mensual promedio** (+ MSE en USD²)
- [x] Métrica de ranking: Gini (temporada baja normal vs caída atípica)
- [x] Visualización: real vs predicción + banda frente a los 2 años de test (`sales_forecast.png`)
- [x] Prueba unitaria: split honesto, 24 predicciones, banda ordenada (`lo <= pred <= hi`)

> Resultados (2026-09-29, `uv run python scripts/train_sales_model.py`):
> RMSE 159 628 USD = **4.74%** del ingreso mensual promedio · MSE 25 481 151 346 USD² · **Gini 0.962**.
> La banda p10–p90 contiene la mayoría de los meses reales; el pico de fin de 2025
> queda fuera — límite honesto del modelo, no sobreajuste.
> Artefactos gitignored: `sales_rf_model.joblib`, `sales_metrics.json`,
> `sales_predictions.csv`, `sales_forecast.png`.

> Nota de entorno: en este equipo Windows la ruta profunda del repo choca con el
> límite MAX_PATH (260) y rompe la importación de sklearn en el venv. Validación
> ejecutada vía unidad `W:` (`subst`) — ver memoria del hito si se repite.

---

## Fase 3 — Evaluación avanzada

> Objetivo: completar las 4 métricas que pide el CONTEXT (§3 y §6): MSE, PSI, Gini,
> K2 Score. Las dos primeras ya están (MSE/RMSE y Gini, Fase 2). Esta fase añade PSI
> y documenta el bloqueo de K2.

### 3.0 PSI (Population Stability Index) — Estabilidad de distribución

- [ ] `population_stability_index(expected, actual, bins=10)` implementada en `scripts/train_sales_model.py`
- [ ] Fórmula por tramos: `Σ (actual% − expected%) × ln(actual% / expected%)`, con épsilon para bins vacíos
- [ ] Bins por cuantiles del set *expected* (train); histograma del set *actual* (test) sobre los mismos bordes
- [ ] `interpret_psi(psi)`: `<0.10` → sin cambio · `0.10–0.25` → moderado · `≥0.25` → fuerte (Siddiqi 2005)
- [ ] Calculada **train-vs-test** sobre `revenue_usd`
- [ ] `sales_metrics.json` extendido con `psi` (float) + `psi_interpretation` (string)
- [ ] Test: PSI ≈ 0 con distribuciones idénticas (`test_psi_zero_with_identical_distributions`)
- [ ] Test: PSI > 0.25 con shift simulado (`test_psi_high_with_shifted_distribution`)
- [ ] Test: todas las métricas se calculan solo sobre los 24 meses de test (`test_all_metrics_computed_only_on_test_months`)

> **Aproximación documentada:** el CONTEXT §3 pide PSI sobre la mezcla de visitas
> US/UK, pero `healthcore_sales.csv` solo contiene filas `consolidated` — no hay
> desglose regional. El PSI implementado compara la distribución de `revenue_usd`
> train-vs-test como proxy de estabilidad. Un PSI regional requiere el split de
> datos descrito en CONTEXT §5 (proporción ~75/25 US/UK) y queda como **TODO**.

### 3.1 K2 Score — ⛔ BLOQUEADO (fórmula no definida)

**Estado:** implementación diferida — la definición/fórmula no existe en ningún
artefacto del proyecto ni en la literatura estándar de ML/estadística.

**Investigación realizada (2026-09-29):**

| Candidata | Qué es | Aplica aquí |
|---|---|---|
| D'Agostino K² | Test de normalidad de residuos (`scipy.stats.normaltest`) | Posible, pero no se llama "K2 Score" en forecasting |
| Cooper-Herskovits K2 | Score de estructura de redes bayesianas | No — es para DAGs, no regresión de series de tiempo |
| R² (coef. determinación) | `1 − SS_res / SS_tot` | Posible typo; semántica distinta a "K2" |
| KS (Kolmogorov-Smirnov) | Test de distribución | Posible confusión de nombre |

**Decisión:** no se inventa una métrica. Cuando el equipo o la rúbrica del bootcamp
proporcione la fórmula oficial, se implementa con su test acorde.

- [ ] Recibir fórmula oficial de K2 Score (fuente: rúbrica bootcamp / tech lead)
- [ ] Implementar en `scripts/train_sales_model.py`
- [ ] Añadir test unitario en `tests/pipelines/test_sales_model.py`
- [ ] Extender `sales_metrics.json` con `k2` (float) + `k2_interpretation` (string)

> Mientras tanto, `sales_metrics.json` incluirá:
> ```json
> "k2": null,
> "k2_status": "blocked_missing_definition"
> ```

### 3.2 Reporte consolidado y cierre

- [ ] `sales_metrics.json` contiene: `mse_usd2`, `rmse_usd`, `rmse_pct_of_mean`, `gini`, `psi`, `psi_interpretation`, `k2` (null hasta desbloqueo)
- [ ] `uv run python -m pytest tests/pipelines/ -q` → todos en verde
- [ ] `uv run python scripts/train_sales_model.py` → métricas actualizadas
- [ ] `git diff --check` limpio

> **Resultados (pendiente ejecución):**
>
> | Métrica | Valor | Lectura para Finanzas |
> |---|---|---|
> | RMSE % | TODO | Desviación mensual típica como % del ingreso promedio |
> | RMSE USD | TODO | Error absoluto mensual — margen de presupuesto |
> | Gini | TODO | Capacidad de ranking: distinguir mes débil de mes fuerte |
> | PSI | TODO | Estabilidad de la distribución de ingresos train→test |
> | K2 | bloqueado | Requiere definición oficial |
