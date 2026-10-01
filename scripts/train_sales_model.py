"""Sales prediction training — HealthCore (honest recursive forecast).

Model: Random Forest (see ROADMAP.es.md §2.0 for the documented choice).

Standalone process — run from the repo root with::

    uv run python scripts/train_sales_model.py

Honesty guarantees::

    1. chronological 8/2 split — forest fits on train years only.
    2. no contemporaneous leakage — ``visits_count`` / ``avg_revenue_per_visit_usd``
       are NOT model features (product ≈ revenue_usd on the same month).
    3. recursive multi-step test forecast — each test month's lags/rollings are
       built from train history + *previous predictions*, never from real test
       revenue (and never from same-month visit/ARPU fields).
    4. variability band = p10-p90 across the forest's own trees.

Artifacts (gitignored runtime data)::

    data/process/sales_forecasting/sales_rf_model.joblib
    data/process/sales_forecasting/sales_metrics.json
    data/process/sales_forecasting/sales_predictions.csv
    data/process/sales_forecasting/sales_forecast.png
    data/process/sales_forecasting/sales_decomposition.png
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

# Calendar only — known at forecast time. Contemporaneous visits/ARPU excluded
# (PR review: same-month product ≈ revenue_usd).
BASE_FEATURES = ["year", "month_sin", "month_cos"]
LEAKY_CONTEMPORANEOUS = ("visits_count", "avg_revenue_per_visit_usd")


def add_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Causal lags/rollings of the target — month t sees only months < t.

    Prefer calling this on the **train block alone**. For the sealed test
    horizon use ``forecast_recursive`` instead of precomputing lags on train+test.
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


def feature_columns(frame: pd.DataFrame | None = None) -> list[str]:
    """Model feature names — calendar + lags/rollings, never leaky contemporaneous."""
    cols = list(BASE_FEATURES) + [f"lag_{lag}" for lag in LAG_MONTHS]
    cols += [f"rolling_mean_{w}" for w in ROLLING_WINDOWS]
    for leaky in LEAKY_CONTEMPORANEOUS:
        if leaky in cols:
            raise ValueError(f"refusing leaky contemporaneous feature: {leaky}")
    if frame is not None:
        missing = [c for c in cols if c not in frame.columns]
        if missing:
            raise ValueError(f"missing feature columns: {missing}")
    return cols


def _features_from_history(calendar_row: pd.Series, history: list[float]) -> dict[str, float]:
    """Build one feature row from calendar fields + revenue history (past only)."""
    if len(history) < max(LAG_MONTHS):
        raise ValueError(
            f"need ≥{max(LAG_MONTHS)} history months for lags, got {len(history)}"
        )
    feats: dict[str, float] = {
        "year": float(calendar_row["year"]),
        "month_sin": float(calendar_row["month_sin"]),
        "month_cos": float(calendar_row["month_cos"]),
    }
    for lag in LAG_MONTHS:
        feats[f"lag_{lag}"] = float(history[-lag])
    for window in ROLLING_WINDOWS:
        feats[f"rolling_mean_{window}"] = float(np.mean(history[-window:]))
    return feats


def train_forest(train_x: pd.DataFrame, train_y: pd.Series,
                 n_estimators: int = N_ESTIMATORS) -> RandomForestRegressor:
    """Fit the forest on train only (fixed seed → deterministic)."""
    model = RandomForestRegressor(
        n_estimators=n_estimators, random_state=RANDOM_STATE, n_jobs=-1
    )
    model.fit(np.asarray(train_x), np.asarray(train_y))
    logger.info("trained RandomForest (trees=%d) on %d rows", n_estimators, len(train_x))
    return model


def predict_row_with_band(model: RandomForestRegressor,
                          row_x: pd.DataFrame) -> tuple[float, float, float]:
    """One-row forest mean + p10-p90 across trees."""
    arr = np.asarray(row_x)
    tree_preds = np.array([tree.predict(arr)[0] for tree in model.estimators_])
    return (
        float(tree_preds.mean()),
        float(np.percentile(tree_preds, LOW_Q)),
        float(np.percentile(tree_preds, HIGH_Q)),
    )


def forecast_recursive(
    model: RandomForestRegressor,
    train_history: pd.Series,
    test_calendar: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """Multi-step test forecast: each step feeds the next with the prediction.

    ``train_history`` = revenue_usd through the last train month (no test).
    ``test_calendar`` = test rows with month + calendar features only.
    Real test ``revenue_usd`` / visits / ARPU are never read here.
    """
    history = [float(v) for v in train_history.tolist()]
    rows: list[dict[str, float]] = []
    for _, cal in test_calendar.iterrows():
        feats = _features_from_history(cal, history)
        row_x = pd.DataFrame([{c: feats[c] for c in feature_cols}])
        pred, lo, hi = predict_row_with_band(model, row_x)
        rows.append({"predicted": pred, "band_lo": lo, "band_hi": hi})
        history.append(pred)  # recursive — not the real test revenue
    return pd.DataFrame(rows)


def predict_with_band(model: RandomForestRegressor,
                      test_x: pd.DataFrame) -> pd.DataFrame:
    """Batch predict + band (train/diagnostics only — not for sealed test)."""
    test_arr = np.asarray(test_x)
    tree_preds = np.stack([tree.predict(test_arr) for tree in model.estimators_], axis=0)
    return pd.DataFrame({
        "predicted": tree_preds.mean(axis=0),
        "band_lo": np.percentile(tree_preds, LOW_Q, axis=0),
        "band_hi": np.percentile(tree_preds, HIGH_Q, axis=0),
    })


def decompose_series(frame: pd.DataFrame, period: int = 12) -> pd.DataFrame:
    """Classical additive decomposition (trend / seasonal / residual).

    Equivalent intent to ``statsmodels.tsa.seasonal_decompose`` without a new
    heavy dependency: 12-month centered moving-average trend + month-of-year
    seasonal means on the detrended series.
    """
    frame = frame.sort_values("month").reset_index(drop=True)
    y = frame[TARGET_COL].astype(float)
    ma = y.rolling(window=period, center=True).mean()
    trend = ma.rolling(window=2, center=True).mean()
    detrended = y - trend
    month_num = frame["month"].dt.month
    seasonal = detrended.groupby(month_num).transform("mean")
    residual = y - trend - seasonal
    return pd.DataFrame({
        "month": frame["month"],
        "observed": y,
        "trend": trend,
        "seasonal": seasonal,
        "residual": residual,
        "month_num": month_num,
    })


def plot_decomposition(decomp: pd.DataFrame, path: Path) -> dict[str, str]:
    """Plot decomposition and return a short CONTEXT-pattern checklist."""
    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(decomp["month"], decomp["observed"], color="black")
    axes[0].set_ylabel("observed")
    axes[1].plot(decomp["month"], decomp["trend"])
    axes[1].set_ylabel("trend")
    axes[2].plot(decomp["month"], decomp["seasonal"])
    axes[2].set_ylabel("seasonal")
    axes[3].plot(decomp["month"], decomp["residual"])
    axes[3].set_ylabel("residual")
    axes[0].set_title(
        "HealthCore revenue_usd — descomposición aditiva (periodo=12)"
    )
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    logger.info("decomposition plot written to %s", path)

    seas = (
        decomp.dropna(subset=["seasonal"])
        .groupby("month_num")["seasonal"]
        .mean()
    )
    peak = sorted(seas.items(), key=lambda kv: kv[1], reverse=True)[:3]
    trough = sorted(seas.items(), key=lambda kv: kv[1])[:3]
    peak_months = [m for m, _ in peak]
    trough_months = [m for m, _ in trough]
    oct_dec = {10, 11, 12}
    jul_aug = {7, 8}
    return {
        "peak_months": ",".join(str(m) for m in peak_months),
        "trough_months": ",".join(str(m) for m in trough_months),
        "matches_context_oct_dec_high": str(bool(oct_dec & set(peak_months))),
        "matches_context_jul_aug_low": str(bool(jul_aug & set(trough_months))),
        "note": (
            "CONTEXT: Oct–Dec +15–20%, Jul–Aug −12–18%. "
            f"Observed seasonal peaks≈{peak_months}, troughs≈{trough_months}."
        ),
    }


def normalized_gini(actual: pd.Series, predicted: pd.Series) -> float:
    """Ranking quality: 1.0 = perfect ordering, 0.0 = random ordering."""
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
    """Population Stability Index — train vs test on revenue_usd (proxy)."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

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
    """R² — adopted team reading of CONTEXT label "K2 Score" (not official)."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    if ss_tot == 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def evaluate(actual: pd.Series, predicted: pd.Series,
             train_revenue: pd.Series | None = None) -> dict:
    """MSE/RMSE/Gini/R² (+ optional PSI) on the sealed test months."""
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
            "Adopted interpretation: CONTEXT label 'K2 Score' reported as R² "
            "(coefficient of determination) — not an official equivalence; "
            "see ROADMAP §3.1"
        ),
        "forecast_mode": "recursive_no_contemporaneous_visits_arpu",
        "n_test_months": int(len(actual)),
    }
    if train_revenue is not None:
        psi = population_stability_index(train_revenue, actual)
        metrics["psi"] = psi
        metrics["psi_interpretation"] = interpret_psi(psi)
    return metrics


def plot_forecast(test_months: pd.Series, actual: pd.Series, forecast: pd.DataFrame,
                  path: Path, metrics: dict | None = None) -> None:
    """Actual vs predicted + variability band over the 2 HealthCore test years."""
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
    ax.plot(test_months, forecast["predicted"], label="Predicción RF (recursiva)", linewidth=2)
    ax.fill_between(
        test_months, forecast["band_lo"], forecast["band_hi"],
        alpha=0.25, label="Banda p10–p90 (árboles RF)",
    )
    ax.set_title(
        "HealthCore — test 2024-01 → 2025-12 (recursivo, sin visits/ARPU contemporáneos)"
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
    base = add_calendar_features(clean_sales(load_sales()))
    # Split BEFORE any lag construction that could touch the test horizon.
    train_raw, test_raw = chronological_split(base, expected=(96, 24))

    decomp = decompose_series(base)

    # Lags for fitting: train block only (no test revenues in lag columns).
    train = add_lag_features(train_raw.copy())
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=n_estimators)

    forecast = forecast_recursive(
        model,
        train_history=train_raw[TARGET_COL],
        test_calendar=test_raw[["month", "year", "month_sin", "month_cos"]],
        feature_cols=cols,
    )
    metrics = evaluate(
        test_raw[TARGET_COL], forecast["predicted"],
        train_revenue=train_raw[TARGET_COL],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    decomp_notes = plot_decomposition(decomp, output_dir / "sales_decomposition.png")
    metrics["decomposition"] = decomp_notes

    joblib.dump({"model": model, "feature_cols": cols}, output_dir / "sales_rf_model.joblib")
    (output_dir / "sales_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.concat(
        [test_raw[["month", TARGET_COL]].reset_index(drop=True), forecast], axis=1
    ).to_csv(output_dir / "sales_predictions.csv", index=False)
    plot_forecast(
        test_raw["month"], test_raw[TARGET_COL], forecast,
        output_dir / "sales_forecast.png", metrics=metrics,
    )
    logger.info(
        "metrics: rmse_usd=%.0f rmse_pct_of_mean=%.2f%% gini=%.3f r2=%.3f psi=%.4f (%s) mode=%s",
        metrics["rmse_usd"], metrics["rmse_pct_of_mean"], metrics["gini"],
        metrics["r2"], metrics["psi"], metrics["psi_interpretation"],
        metrics["forecast_mode"],
    )
    logger.info("decomposition: %s", decomp_notes.get("note", ""))
    return metrics


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Train HealthCore sales RF (honest recursive test forecast)."
    )
    parser.add_argument("--n-estimators", type=int, default=N_ESTIMATORS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    run(n_estimators=args.n_estimators, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
