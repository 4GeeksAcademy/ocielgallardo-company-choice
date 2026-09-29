"""Sales prediction training — Phase 2 (Ticket: sales prediction model).

Model: Random Forest (see ROADMAP.es.md §2.0 for the documented choice).

Standalone process — run from the repo root with::

    uv run python scripts/train_sales_model.py

Honesty guarantees (same as Phase 1, extended)::

    1. causal features only — every lag/rolling at month t uses months < t,
       so computing them on the continuous series before the split leaks nothing.
    2. the forest trains on 2016-01..2023-12 only; 2024-01..2025-12 are
       predicted unseen (24 months, no shuffle, no refit on test).
    3. variability band = p10-p90 across the forest's own trees (no extra model).

Artifacts (gitignored runtime data)::

    data/process/sales_forecasting/sales_rf_model.joblib
    data/process/sales_forecasting/sales_metrics.json
    data/process/sales_forecasting/sales_predictions.csv
    data/process/sales_forecasting/sales_forecast.png
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from scripts.prepare_sales_data import (
    OUTPUT_DIR,
    TARGET_COL,
    add_calendar_features,
    chronological_split,
    clean_sales,
    load_sales,
)

logger = logging.getLogger("train_sales_model")

RANDOM_STATE = 42
N_ESTIMATORS = 500
LAG_MONTHS = [1, 3, 6, 12]
ROLLING_WINDOWS = [3, 12]
LOW_Q, HIGH_Q = 10, 90

BASE_FEATURES = ["visits_count", "avg_revenue_per_visit_usd", "year", "month_sin", "month_cos"]


def add_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Causal lags/rollings of the target — month t sees only months < t.

    Safe to run on the continuous series before the split: no row ever reads
    a future value. Rows without full history (first 12 months) are dropped;
    they all fall inside train, never in test.
    """
    frame = frame.sort_values("month").reset_index(drop=True)
    for lag in LAG_MONTHS:
        frame[f"lag_{lag}"] = frame[TARGET_COL].shift(lag)
    for window in ROLLING_WINDOWS:
        frame[f"rolling_mean_{window}"] = frame[TARGET_COL].shift(1).rolling(window).mean()
    before = len(frame)
    frame = frame.dropna().reset_index(drop=True)
    logger.info("lag features: dropped %d rows without full history", before - len(frame))
    return frame


def feature_columns(frame: pd.DataFrame) -> list[str]:
    cols = BASE_FEATURES + [f"lag_{lag}" for lag in LAG_MONTHS]
    cols += [f"rolling_mean_{w}" for w in ROLLING_WINDOWS]
    missing = [c for c in cols if c not in frame.columns]
    if missing:
        raise ValueError(f"missing feature columns: {missing}")
    return cols


def train_forest(train_x: pd.DataFrame, train_y: pd.Series,
                 n_estimators: int = N_ESTIMATORS) -> RandomForestRegressor:
    """Fit the forest on train only (fixed seed → deterministic)."""
    model = RandomForestRegressor(
        n_estimators=n_estimators, random_state=RANDOM_STATE, n_jobs=-1
    )
    model.fit(np.asarray(train_x), np.asarray(train_y))
    logger.info("trained RandomForest (trees=%d) on %d rows", n_estimators, len(train_x))
    return model


def predict_with_band(model: RandomForestRegressor,
                      test_x: pd.DataFrame) -> pd.DataFrame:
    """Point prediction (forest mean) + p10-p90 band from the trees' votes."""
    test_arr = np.asarray(test_x)
    tree_preds = np.stack([tree.predict(test_arr) for tree in model.estimators_], axis=0)
    return pd.DataFrame({
        "predicted": tree_preds.mean(axis=0),
        "band_lo": np.percentile(tree_preds, LOW_Q, axis=0),
        "band_hi": np.percentile(tree_preds, HIGH_Q, axis=0),
    })


def normalized_gini(actual: pd.Series, predicted: pd.Series) -> float:
    """Ranking quality: 1.0 = perfect ordering, 0.0 = random ordering.

    Normalized Gini = Gini(pred-order) / Gini(actual-order); tells Sandra
    whether the model ranks a weak August below a strong December.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    def _gini(order: np.ndarray) -> float:
        ranked = actual[np.argsort(order)]
        n = len(ranked)
        cum = np.cumsum(ranked)
        if cum[-1] == 0:
            return 0.0
        lorenz = cum / cum[-1]
        return 1.0 - 2.0 * lorenz.mean() + 1.0 / n

    denom = _gini(actual)
    return _gini(predicted) / denom if denom != 0 else 0.0


def evaluate(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """MSE in USD² (CONTEXT), RMSE in USD and RMSE as % of mean monthly revenue.

    ``rmse_pct_of_mean = rmse / mean_revenue * 100`` — the Finanzas-readable
    number: "our typical monthly miss is X% of a normal month's revenue".
    RMSE (not MSE) is used for the percentage so units match (USD/USD).
    """
    actual = actual.astype(float)
    predicted = predicted.astype(float)
    mse = float(((actual - predicted) ** 2).mean())
    rmse = float(np.sqrt(mse))
    mean_revenue = float(actual.mean())
    return {
        "mse_usd2": mse,
        "rmse_usd": rmse,
        "mean_monthly_revenue_usd": mean_revenue,
        "rmse_pct_of_mean": rmse / mean_revenue * 100 if mean_revenue else float("nan"),
        "gini": float(normalized_gini(actual, predicted)),
        "n_test_months": int(len(actual)),
    }


def plot_forecast(test_months: pd.Series, actual: pd.Series, forecast: pd.DataFrame,
                  path: Path) -> None:
    """Actual vs predicted + variability band over the 2 test years."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(test_months, actual, label="Real", linewidth=2)
    ax.plot(test_months, forecast["predicted"], label="Predicción RF", linewidth=2)
    ax.fill_between(test_months, forecast["band_lo"], forecast["band_hi"],
                    alpha=0.25, label="Banda p10–p90")
    ax.set_title("Ventas 2024–2025: real vs predicción (test no visto)")
    ax.set_xlabel("Mes")
    ax.set_ylabel("Revenue USD")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    logger.info("plot written to %s", path)


def run(n_estimators: int = N_ESTIMATORS,
        output_dir: Path = OUTPUT_DIR) -> dict[str, float]:
    frame = add_lag_features(add_calendar_features(clean_sales(load_sales())))
    # 108 rows after dropping the 12-month lag warm-up (all inside train).
    train, test = chronological_split(frame, expected=(84, 24))
    cols = feature_columns(frame)

    model = train_forest(train[cols], train[TARGET_COL], n_estimators=n_estimators)
    forecast = predict_with_band(model, test[cols])
    metrics = evaluate(test[TARGET_COL], forecast["predicted"])

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": cols}, output_dir / "sales_rf_model.joblib")
    (output_dir / "sales_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.concat([test[["month", TARGET_COL]].reset_index(drop=True), forecast], axis=1).to_csv(
        output_dir / "sales_predictions.csv", index=False
    )
    plot_forecast(test["month"], test[TARGET_COL], forecast,
                  output_dir / "sales_forecast.png")
    logger.info("metrics: rmse_usd=%.0f rmse_pct_of_mean=%.2f%% gini=%.3f",
                metrics["rmse_usd"], metrics["rmse_pct_of_mean"], metrics["gini"])
    return metrics


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Train HealthCore sales RF (Phase 2).")
    parser.add_argument("--n-estimators", type=int, default=N_ESTIMATORS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    run(n_estimators=args.n_estimators, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
