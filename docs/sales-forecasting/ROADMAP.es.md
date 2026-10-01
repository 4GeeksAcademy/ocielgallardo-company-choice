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
- [x] Calendario: `year`, `month_sin/cos` (BASE_FEATURES)
- [~] Legacy Fase 2: `visits_count` / `avg_revenue_per_visit_usd` como features — **retiradas en Fase 5.1** (fuga contemporánea; ver §5.1)
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
> K2 Score. MSE/RMSE y Gini llegaron en Fase 2; esta fase añade PSI y resuelve
> K2 Score como R² (coeficiente de determinación).

> **Nota (por qué un MSE bajo no basta solo):**
> El MSE solo dice "en promedio, ¿cuánto nos equivocamos en dólares?".
> Eso es útil, pero no alcanza para confiar en el modelo:
>
> 1. Un error pequeño puede salir de **memorizar el pasado** (sobreajuste).
>    Por eso evaluamos en 24 meses que el modelo **nunca vio**.
> 2. El MSE no dice si el modelo **ordena bien** los meses (Agosto débil vs
>    Diciembre fuerte). Eso lo mira el **Gini**.
> 3. El MSE no avisa si los datos de prueba **ya no se parecen** a los de
>    entrenamiento. Eso lo mira el **PSI**.
> 4. El MSE no dice **qué parte de la variación** de ingresos captura el
>    modelo. Eso lo mira el **R²** (nuestra lectura del K2 Score).
>
> En corto: MSE = tamaño del error. Las otras métricas = si ese error es
> honesto, útil y estable. Finanzas necesita las cuatro, no solo un número
> bonito.

### 3.0 PSI (Population Stability Index) — Estabilidad de distribución

- [x] `population_stability_index(expected, actual, bins=10)` implementada en `scripts/train_sales_model.py`
- [x] Fórmula por tramos: `Σ (actual% − expected%) × ln(actual% / expected%)`, con épsilon para bins vacíos
- [x] Bins por cuantiles del set *expected* (train); histograma del set *actual* (test) sobre los mismos bordes
- [x] `interpret_psi(psi)`: `<0.10` → sin cambio · `0.10–0.25` → moderado · `≥0.25` → fuerte (Siddiqi 2005)
- [x] Calculada **train-vs-test** sobre `revenue_usd`
- [x] `sales_metrics.json` extendido con `psi` (float) + `psi_interpretation` (string)
- [x] Test: PSI ≈ 0 con distribuciones idénticas (`test_psi_zero_with_identical_distributions`)
- [x] Test: PSI > 0.25 con shift simulado (`test_psi_high_with_shifted_distribution`)
- [x] Test: todas las métricas se calculan solo sobre los 24 meses de test (`test_all_metrics_computed_only_on_test_months`)

> **Aproximación documentada:** el CONTEXT §3 pide PSI sobre la mezcla de visitas
> US/UK, pero `healthcore_sales.csv` solo contiene filas `consolidated` — no hay
> desglose regional. El PSI implementado compara la distribución de `revenue_usd`
> train-vs-test como proxy de estabilidad. Un PSI regional requiere el split de
> datos descrito en CONTEXT §5 (proporción ~75/25 US/UK) y queda como **TODO**.

### 3.1 K2 Score — interpretación adoptada como R² (no equivalencia oficial)

> **Legacy (bloqueo 2026-09-29):** la fórmula no estaba en CONTEXT ni en literatura
> estándar bajo el nombre "K2 Score". Candidatas investigadas: D'Agostino K²
> (normalidad de residuos), Cooper-Herskovits K2 (redes bayesianas), R², KS.
> Se documentó el bloqueo y se pidió la definición oficial antes de inventar nada.

**Decisión del equipo (2026-09-29, aclarada tras review):** reportar **R²** bajo la
etiqueta CONTEXT "K2 Score" como **interpretación adoptada del equipo**, no como
equivalencia oficial documentada por HealthCore. Motivos:

1. **Complementa las otras tres sin redundancia.** MSE responde "¿cuánto erramos
   en USD?"; Gini, "¿rankea bien meses débiles vs fuertes?"; PSI, "¿cambió la
   distribución train→test?". R² responde la pregunta que falta: "¿qué proporción
   de la variabilidad de ingresos captura el modelo?".
2. **Explicable a Finanzas en una frase.** "El modelo explica el X% de la
   variación mensual" — cumple el criterio no negociable del ticket ("métrica
   que yo pueda explicarle a Finanzas sin que parezca una caja negra").
3. **Hipótesis de typo K↔R** en teclado QWERTY; no existe métrica estándar de
   forecasting llamada "K2 Score". R² es la lectura natural en un set de
   evaluación de regresión.
4. **Fórmula oficial de R², sin inventar:** `R² = 1 − SS_res / SS_tot`, con media
   tomada solo del set de test (evaluación honesta).

- [x] Decisión documentada: etiqueta K2 → R² como interpretación adoptada (este §3.1)
- [x] `r2_score(actual, predicted)` implementada en `scripts/train_sales_model.py`
- [x] Test: R² = 1.0 con predicción perfecta; parcial en (0, 1) (`test_r2_perfect_prediction`)
- [x] `sales_metrics.json` incluye `r2` (float) + `k2_note` (trazabilidad: adopted, not official)

### 3.2 Reporte consolidado y cierre

- [x] `sales_metrics.json` contiene: `mse_usd2`, `rmse_usd`, `rmse_pct_of_mean`, `gini`, `r2`, `k2_note`, `psi`, `psi_interpretation`
- [x] `uv run python -m pytest tests/pipelines/ -q` → 35 passed (vía `subst W:`)
- [x] `uv run python scripts/train_sales_model.py` → métricas actualizadas
- [x] `git diff --check` limpio

> **Resultados (2026-09-29, `uv run python scripts/train_sales_model.py` vía `W:`):**
>
> | Métrica | Valor | Lectura para Finanzas |
> |---|---|---|
> | RMSE % | **4.74%** | Desviación mensual típica ≈ 5% del ingreso promedio |
> | RMSE USD | **159 628** | Error absoluto mensual — margen de presupuesto ±160K |
> | Gini | **0.962** | Distingue meses débiles de fuertes con alta confianza |
> | PSI | **5.04** (`significant_shift`) | La distribución de `revenue_usd` cambió train→test (crecimiento anual ~4% desplaza la masa); proxy consolidado, no mezcla US/UK |
> | R² (K2) | **0.799** | El modelo captura ~80% de la variabilidad de ingresos en test |
>
> **TODOs honestos:** PSI regional (CSV sin desglose US/UK); el pico de fin de 2025
> sigue fuera de la banda p10–p90 (límite del modelo, no sobreajuste).

---

## Fase 4 — Visualización

> Entregable CONTEXT §6: predicción + rango de variabilidad frente a los datos
> reales de los 2 años de prueba (`month`, `revenue_usd`).

### 4.0 Gráfico HealthCore (solo test)

- [x] `plot_forecast` endurecido en `scripts/train_sales_model.py`
- [x] Solo los **24 meses de test** (2024-01 → 2025-12); aserción `len == 24`
- [x] Ejes CONTEXT: x = `month`, y = `revenue_usd` (USD)
- [x] Series: real (`revenue_usd`) vs predicción RF (media del bosque)
- [x] Área de variabilidad: banda p10–p90 entre árboles RF (`band_lo` / `band_hi`)
- [x] Título explícito HealthCore + anotación `rmse_pct_of_mean` para Finanzas
- [x] Artefacto: `data/process/sales_forecasting/sales_forecast.png` (gitignored)
- [x] Test: `test_forecast_plot_written_for_24_test_months` (PNG > 0 bytes, 24 filas)

> **Nota:** la banda p10–p90 es la dispersión entre los árboles del Random Forest,
> no un intervalo de confianza bayesiano. Sirve para mostrar a Finanzas un rango
> de incertidumbre, no un único número optimista.

> **Resultado (2026-09-29, vía `subst W:`):** PNG regenerado (~84 KB);
> `pytest` 36 passed; `git diff --check` limpio. El gráfico muestra
> `revenue_usd` real vs predicción RF + banda p10–p90 en los 24 meses de test,
> con anotación RMSE 4.74% del ingreso mensual medio.

---

## Fase 5 — Pruebas (split 8/2 + anti-fuga)

> Entregable del ticket: al menos una prueba unitaria en `tests/pipelines/` que
> valide el split 8 años train / 2 años test y que no haya data leakage entre
> ambos conjuntos.

### 5.0 Tests de honestidad del split

- [x] `test_split_is_96_train_24_test_on_date_boundary` — conteos y límites de calendario
- [x] `test_no_month_leaks_between_train_and_test` — frontera estricta + intersección vacía
- [x] `test_scaler_is_fitted_on_train_only` — estadísticas de escalado sin test
- [x] **Aceptación ticket:** `test_eight_two_year_split_has_no_data_leakage`
  (8/2 + sin meses compartidos + scaler ≠ media de la serie completa)
- [x] Pipeline con lags: `test_train_never_sees_test_years` (84/24 post warm-up)
- [x] Features causales: `test_lag_features_are_causal` (mes t no lee meses ≥ t)

> Archivo: `tests/pipelines/test_sales_split.py` (+ checks de modelo en
> `test_sales_model.py`).

> **Resultado (2026-09-29, vía `subst W:`):** `pytest tests/pipelines tests/nightly`
> → **37 passed**; `git diff --check` limpio.

---

## Fase 5.1 — Forecast honesto (PR review: fuga + descomposición)

> Corrección post-review: el split 8/2 era cronológico, pero el test aún podía
> "ver" el presente vía (a) `visits_count` × `avg_revenue_per_visit_usd` ≈
> `revenue_usd` del mismo mes, y (b) lags construidos sobre train+test con el
> `revenue_usd` real de test (batch predict). Esto inflaba RMSE/R².

### 5.1.0 Sin features contemporáneas leaky

- [x] `BASE_FEATURES = year, month_sin, month_cos` únicamente
- [x] `LEAKY_CONTEMPORANEOUS = (visits_count, avg_revenue_per_visit_usd)` excluidas
- [x] `feature_columns()` rechaza esas columnas si aparecen
- [x] Test: `test_feature_columns_exclude_leaky_contemporaneous`

### 5.1.1 Forecast recursivo en test (sellado)

- [x] Lags de entrenamiento solo sobre el bloque train (`add_lag_features(train_raw)`)
- [x] `forecast_recursive`: cada mes de test alimenta el siguiente con la **predicción**,
  nunca con `revenue_usd` real ni visits/ARPU del mes
- [x] Tests: banda ordenada 24 meses; `lag_1` del mes 1 = predicción del mes 0 ≠ real
- [x] `forecast_mode` en métricas: `recursive_no_contemporaneous_visits_arpu`

### 5.1.2 Descomposición estacional vs CONTEXT HealthCore

- [x] `decompose_series` aditiva periodo=12 (sin statsmodels)
- [x] Artefacto: `sales_decomposition.png`
- [x] Checklist vs CONTEXT (Oct–Dec alto, Jul–Aug bajo) en `metrics["decomposition"]`
- [x] Test: `test_decomposition_matches_healthcore_seasonality_pattern`

### 5.1.3 K2 wording + métricas honestas

- [x] `k2_note` / ROADMAP §3.1: R² = interpretación adoptada, no equivalencia oficial
- [x] Re-entrenar y documentar RMSE/Gini/R²/PSI **post-fuga** (tabla abajo)

> **Resultados honestos (2026-10-01, `uv run python scripts/train_sales_model.py` vía `W:`):**
>
> | Métrica | Valor (batch leaky, legacy) | Valor (recursivo limpio) | Lectura |
> |---|---|---|---|
> | RMSE % | ~4.74% | **5.90%** | Sube al quitar fuga contemporánea + usar lags predichos |
> | RMSE USD | ~159 628 | **198 559** | Margen de presupuesto más realista ≈ ±200K |
> | Gini | ~0.962 | **0.899** | Sigue distinguiendo meses débiles/fuertes |
> | R² (adopted K2) | ~0.799 | **0.688** | Captura ~69% de la variabilidad (honesto) |
> | PSI | ~5.04 | **5.10** (`significant_shift`) | Proxy train→test sin cambio material |
>
> Descomposición: picos estacionales **10/11/12**, valles **7/8/9** — alinea con
> CONTEXT Oct–Dec alto / Jul–Aug bajo (`matches_context_* = True`).
>
> Validación: `pytest tests/pipelines/` → **27 passed**; `git diff --check` limpio.
>
> **TODO:** purge gap en CV temporal (evaluación formal en otra rama si aplica).
