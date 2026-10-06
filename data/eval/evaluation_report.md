# Evaluation Report — HealthCore Sales Forecast

**Model:** `RandomForestRegressor` (`n_estimators=500`, `random_state=42`)  
**Target:** `revenue_usd` (CONTEXT: consolidated monthly revenue)  
**Script:** `uv run python scripts/evaluate_sales_model.py`  
**Learning curve image:** [`learning_curve.png`](./learning_curve.png)

## 1. Diagnosis (explicit)

**Classification: overfitting**

Persistent train/validation gap (mean_gap=11.04%, last train=1.45%, last val=9.12%).

Evidence:
- Learning-curve mean train/val RMSE gap ≈ **11.04** percentage points.
- Last curve point: train RMSE **1.45%**, val RMSE **9.12%**.
- Last curve point: train MAE **1.21%**, val MAE **7.53%**.
- Temporal CV stability: **stable** (val RMSE % std = 1.11%).

## 2. Metric selection (MAE vs RMSE)

Primary metric = RMSE (also reported as % of mean monthly revenue_usd). HealthCore CONTEXT asks for MSE/RMSE in USD² and as % of mean monthly revenue so Tom (Revenue Cycle) and Sandra (CEO) can read budget risk without translation. RMSE penalizes large month-level misses more than MAE — those spikes matter for capacity planning around flu season (Oct–Dec) vs summer troughs (Jul–Aug). MAE is reported as a secondary, easier-to-explain average dollar miss. Working assumption (ROADMAP §2.4): underestimating demand is the costlier side for clinic capacity; directional bias (prediction − actual) is tracked alongside RMSE.

| Role | Metric | CV result (mean ± std) |
| --- | --- | --- |
| **Primary** | RMSE % of mean `revenue_usd` | **7.41% ± 1.11%** |
| Primary (USD) | RMSE USD | **216271.58 USD ± 34849.06 USD** |
| Secondary | MAE % of mean `revenue_usd` | **6.31% ± 1.49%** |
| Secondary (USD) | MAE USD | **184486.35 USD ± 44643.94 USD** |

Train-side CV means (in-sample, diagnostic only):  
RMSE % = 1.41% ± 0.27%; MAE % = 1.19% ± 0.22%.

## 3. Temporal cross-validation (≥5 folds)

- Splitter: `TimeSeriesSplit(n_splits=5, test_size=12, gap=12)`
- **Shuffle:** false (chronological order preserved; verified by unit test)
- **Lag/rolling leakage:** features rebuilt with `add_lag_features` on **each fold's train rows only**; validation uses recursive forecast; `gap=12` purges `lag_12` across the boundary
- Scope: 8-year train block only; sealed 2024–2025 test **excluded** from CV

| Fold | Train end | Val window | Val RMSE % | Val MAE % | Bias % | % under |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0 | 2017-12-01 | 2019-01-01→2019-12-01 | 6.45 | 4.61 | -3.80 | 75.0 |
| 1 | 2018-12-01 | 2020-01-01→2020-12-01 | 9.20 | 8.70 | -8.70 | 100.0 |
| 2 | 2019-12-01 | 2021-01-01→2021-12-01 | 6.75 | 5.69 | -2.12 | 58.3 |
| 3 | 2020-12-01 | 2022-01-01→2022-12-01 | 6.43 | 5.27 | -5.13 | 83.3 |
| 4 | 2021-12-01 | 2023-01-01→2023-12-01 | 8.21 | 7.29 | -3.83 | 66.7 |

**Summary:** val RMSE % = **7.41% ± 1.11%**; val MAE % = **6.31% ± 1.49%**.

## 4. Learning curve

Fixed validation window = last 24 months of the train block (2022-01 → 2023-12), with a 12-month purge gap before train prefixes of 36 / 48 / 60 months.

| Train months | Train RMSE % | Val RMSE % | Train MAE % | Val MAE % |
| ---: | ---: | ---: | ---: | ---: |
| 36 | 1.11 | 18.21 | 0.96 | 17.66 |
| 48 | 1.18 | 9.52 | 0.99 | 7.24 |
| 60 | 1.45 | 9.12 | 1.21 | 7.53 |

See [`learning_curve.png`](./learning_curve.png). Pattern: low train error vs higher validation error → supports the **overfitting** diagnosis.

## 5. Corrective action (specific)

**Action:** Constrain the forest: set max_depth=6 and min_samples_leaf=3 on RandomForestRegressor (random_state=42 unchanged), re-run this evaluation script, and keep the change only if CV val_rmse_pct mean falls and mean_gap_rmse_pct shrinks below 4%.

**Why this (not a generic tip):** A persistent train≪validation gap indicates memorization; the first lever is reducing tree complexity, not adding features or estimators.

**Business / bias note:** Directional bias leans toward underestimation (mean bias=-4.72% of mean revenue, 76.7% of fold months underestimated). For capacity planning this is the costlier side — monitor sealed-test bias before promoting, even if fit_label is acceptable.

**Stability note:** CV val_rmse_pct std=1.11% ≤ 3.0% — fold performance is acceptably stable.

## 6. Staging verdict

Do **not** promote the unconstrained RF to staging on sealed-test RMSE alone. Apply the corrective action above, re-run this script, and attach updated `learning_curve.png` + this report.

## 7. Reproduce

```bash
# Windows deep paths: use subst W: if sklearn fails (MAX_PATH).
uv run python scripts/evaluate_sales_model.py
uv run python -m pytest tests/pipelines/test_sales_evaluation.py -q
```
