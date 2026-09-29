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


def population_stability_index(
    expected: np.ndarray | pd.Series,
    actual: np.ndarray | pd.Series,
    bins: int = 10,
    eps: float = 1e-4,
) -> float:
    """Population Stability Index — distribution shift between train and test.

    Formula per bin: ``Σ (actual% − expected%) × ln(actual% / expected%)``.
    Empty-bin proportions are floored at *eps* so the log stays finite.

    **Approximation caveat:** CONTEXT §3 asks for PSI on the US/UK visit mix,
    but ``healthcore_sales.csv`` only contains ``consolidated`` rows — no
    regional breakdown. This PSI is computed on *revenue_usd* (train vs test)
    as a proxy; a regional PSI needs the split described in CONTEXT §5 (TODO).

    Standard thresholds (Siddiqi 2005):
        PSI < 0.10  → no significant shift
        0.10 ≤ PSI < 0.25 → moderate shift — investigate
        PSI ≥ 0.25 → significant shift — retrain / escalate
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

    # Bin edges from the *expected* (train) distribution — quantile-based.
    quantiles = np.linspace(0, 100, bins + 1)
    bin_edges = np.unique(np.percentile(expected, quantiles))
    if len(bin_edges) < 2:
        return 0.0
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    exp_counts = np.histogram(expected, bins=bin_edges)[0].astype(float)
    act_counts = np.histogram(actual, bins=bin_edges)[0].astype(float)

    exp_pct = exp_counts / exp_counts.sum()
    act_pct = act_counts / act_counts.sum()

    exp_pct = np.maximum(exp_pct, eps)
    act_pct = np.maximum(act_pct, eps)

    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def interpret_psi(psi: float) -> str:
    """Human-readable PSI interpretation (Siddiqi 2005 thresholds)."""
    if psi < 0.10:
        return "no_shift"
    if psi < 0.25:
        return "moderate_shift"
    return "significant_shift"


def r2_score(actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray) -> float:
    """Coefficient of determination — CONTEXT "K2 Score" resolved as R².

    ``R² = 1 − SS_res / SS_tot``, with mean taken from *actual* only (test
    months). Tells Finanzas what share of revenue variability the model
    captures. See ROADMAP.es.md §3.1 for the decision rationale; the prior
    "blocked_missing_definition" note is kept there as legacy.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    if ss_tot == 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def evaluate(actual: pd.Series, predicted: pd.Series,
             train_revenue: pd.Series | None = None) -> dict:
    """MSE in USD² (CONTEXT), RMSE in USD and RMSE as % of mean monthly revenue.

    ``rmse_pct_of_mean = rmse / mean_revenue * 100`` — the Finanzas-readable
    number: "our typical monthly miss is X% of a normal month's revenue".
    RMSE (not MSE) is used for the percentage so units match (USD/USD).

    Also reports: normalized Gini, R² (CONTEXT "K2 Score"), and — when
    *train_revenue* is given — PSI train-vs-test on ``revenue_usd``.
    """
    actual = actual.astype(float)
    predicted = predicted.astype(float)
    mse = float(((actual - predicted) ** 2).mean())
    rmse = float(np.sqrt(mse))
    mean_revenue = float(actual.mean())
    metrics: dict = {
        "mse_usd2": mse,
        "rmse_usd": rmse,
        "mean_monthly_revenue_usd": mean_revenue,
        "rmse_pct_of_mean": rmse / mean_revenue * 100 if mean_revenue else float("nan"),
        "gini": float(normalized_gini(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
        "k2_note": (
            "K2 Score resolved as R2 (coefficient of determination) — see ROADMAP §3.1"
        ),
        "n_test_months": int(len(actual)),
    }
    if train_revenue is not None:
        psi = population_stability_index(train_revenue, actual)
        metrics["psi"] = psi
        metrics["psi_interpretation"] = interpret_psi(psi)
    return metrics


def plot_forecast(test_months: pd.Series, actual: pd.Series, forecast: pd.DataFrame,
                  path: Path, metrics: dict | None = None) -> None:
    """Actual vs predicted + variability band over the 2 HealthCore test years.

    CONTEXT columns only: ``month`` on the x-axis, ``revenue_usd`` on the y-axis.
    The band is the p10–p90 spread across Random Forest trees (not a Bayesian CI).
    """
    if len(test_months) != 24:
        raise ValueError(
            f"plot expects exactly 24 test months (2024-01..2025-12), got {len(test_months)}"
        )
    if not (
        (forecast["band_lo"] <= forecast["predicted"])
        & (forecast["predicted"] <= forecast["band_hi"])
    ).all():
        raise ValueError("band must satisfy band_lo <= predicted <= band_hi on every month")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(test_months, actual, label="Real (revenue_usd)", linewidth=2)
    ax.plot(test_months, forecast["predicted"], label="Predicción RF", linewidth=2)
    ax.fill_between(
        test_months, forecast["band_lo"], forecast["band_hi"],
        alpha=0.25, label="Banda p10–p90 (árboles RF)",
    )
    ax.set_title(
        "HealthCore — ventas test 2024-01 → 2025-12 "
        "(24 meses no vistos): real vs predicción RF"
    )
    ax.set_xlabel("month")
    ax.set_ylabel("revenue_usd (USD)")
    if metrics and "rmse_pct_of_mean" in metrics:
        ax.annotate(
            f"RMSE = {metrics['rmse_pct_of_mean']:.2f}% del ingreso mensual medio",
            xy=(0.02, 0.97), xycoords="axes fraction",
            ha="left", va="top", fontsize=9,
        )
    ax.legend(loc="upper right")
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
    metrics = evaluate(
        test[TARGET_COL], forecast["predicted"], train_revenue=train[TARGET_COL]
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": cols}, output_dir / "sales_rf_model.joblib")
    (output_dir / "sales_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.concat([test[["month", TARGET_COL]].reset_index(drop=True), forecast], axis=1).to_csv(
        output_dir / "sales_predictions.csv", index=False
    )
    plot_forecast(
        test["month"], test[TARGET_COL], forecast,
        output_dir / "sales_forecast.png", metrics=metrics,
    )
    logger.info(
        "metrics: rmse_usd=%.0f rmse_pct_of_mean=%.2f%% gini=%.3f r2=%.3f psi=%.4f (%s)",
        metrics["rmse_usd"], metrics["rmse_pct_of_mean"], metrics["gini"],
        metrics["r2"], metrics["psi"], metrics["psi_interpretation"],
    )
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
