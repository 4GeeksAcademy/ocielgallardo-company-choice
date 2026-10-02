"""Unit tests for the sales-forecasting training honesty (Phase 2–4 + leak fix).

Under test (Ticket: sales prediction model + PR review):

- the forest trains on 2016-2023 only; the 24 test months are predicted unseen.
- lag/rolling features are causal (month t never reads months >= t).
- no contemporaneous visits/ARPU in model features.
- test forecast is recursive (lags from predictions, not real test revenue).
- the forecast has 24 rows with an ordered band (lo <= predicted <= hi).
- metrics are computed on test only.

Run:
    uv run python -m pytest tests/pipelines/test_sales_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.prepare_sales_data import (  # noqa: E402
    TARGET_COL,
    add_calendar_features,
    chronological_split,
    clean_sales,
    load_sales,
)
from scripts.train_sales_model import (  # noqa: E402
    BASE_FEATURES,
    LEAKY_CONTEMPORANEOUS,
    add_lag_features,
    decompose_series,
    evaluate,
    feature_columns,
    forecast_recursive,
    interpret_psi,
    k2_score,
    plot_forecast,
    population_stability_index,
    r2_score,
    train_forest,
)

TEST_TREES = 20


def _train_test_raw():
    base = add_calendar_features(clean_sales(load_sales()))
    return chronological_split(base, expected=(96, 24))


def _trained():
    train_raw, test_raw = _train_test_raw()
    train = add_lag_features(train_raw.copy())
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=TEST_TREES)
    forecast = forecast_recursive(
        model,
        train_history=train_raw[TARGET_COL],
        test_calendar=test_raw[["month", "year", "month_sin", "month_cos"]],
        feature_cols=cols,
    )
    return train_raw, test_raw, train, cols, model, forecast


def test_lag_features_are_causal():
    train_raw, _ = _train_test_raw()
    frame = add_lag_features(train_raw.copy())
    row = frame[frame["month"] == pd.Timestamp("2017-01-01")].iloc[0]
    raw = train_raw.set_index("month")
    assert row["lag_1"] == raw.loc[pd.Timestamp("2016-12-01"), TARGET_COL]
    assert row["lag_12"] == raw.loc[pd.Timestamp("2016-01-01"), TARGET_COL]
    assert frame["month"].min() == pd.Timestamp("2017-01-01")


def test_train_never_sees_test_years():
    train_raw, test_raw = _train_test_raw()
    assert train_raw["month"].max() < pd.Timestamp("2024-01-01")
    assert test_raw["month"].min() >= pd.Timestamp("2024-01-01")
    assert len(train_raw) == 96
    assert len(test_raw) == 24


def test_feature_columns_exclude_leaky_contemporaneous():
    cols = feature_columns()
    for leaky in LEAKY_CONTEMPORANEOUS:
        assert leaky not in cols
    for cal in BASE_FEATURES:
        assert cal in cols


def test_forecast_recursive_has_ordered_band_over_24_months():
    _, _, _, _, _, forecast = _trained()
    assert len(forecast) == 24
    assert ((forecast["band_lo"] <= forecast["predicted"])
            & (forecast["predicted"] <= forecast["band_hi"])).all()


def test_recursive_forecast_does_not_use_real_test_revenue_in_lags():
    """Second test month's lag_1 must equal the *prediction* of the first, not real Y."""
    train_raw, test_raw, _, _, _, forecast = _trained()
    from scripts.train_sales_model import _features_from_history

    history = [float(v) for v in train_raw[TARGET_COL].tolist()]
    pred0 = float(forecast.iloc[0]["predicted"])
    real0 = float(test_raw.iloc[0][TARGET_COL])
    feats1 = _features_from_history(test_raw.iloc[1], history + [pred0])
    assert feats1["lag_1"] == pred0
    assert abs(pred0 - real0) > 1.0, "sanity: first prediction should differ from real"
    assert feats1["lag_1"] != real0


def test_metrics_follow_documented_formula():
    train_raw, test_raw, _, _, _, forecast = _trained()
    metrics = evaluate(test_raw[TARGET_COL], forecast["predicted"])
    assert metrics["n_test_months"] == 24
    assert metrics["mse_usd2"] > 0
    assert metrics["rmse_usd"] == metrics["mse_usd2"] ** 0.5
    assert metrics["rmse_pct_of_mean"] == (
        metrics["rmse_usd"] / metrics["mean_monthly_revenue_usd"] * 100
    )
    assert 0.0 <= metrics["gini"] <= 1.0
    assert "k2" in metrics and "k2_pvalue" in metrics
    assert metrics["k2_interpretation"] in (
        "residuals_look_normal", "residuals_non_normal",
    )
    assert "r2" in metrics  # bonus
    assert metrics["forecast_mode"] == "recursive_no_contemporaneous_visits_arpu"


def test_psi_zero_with_identical_distributions():
    rng = np.random.RandomState(42)
    data = rng.normal(loc=100_000, scale=10_000, size=200)
    psi = population_stability_index(data, data)
    assert psi < 0.01
    assert interpret_psi(psi) == "no_shift"


def test_psi_high_with_shifted_distribution():
    rng = np.random.RandomState(42)
    expected = rng.normal(loc=100_000, scale=10_000, size=200)
    actual = rng.normal(loc=200_000, scale=10_000, size=200)
    psi = population_stability_index(expected, actual)
    assert psi > 0.25
    assert interpret_psi(psi) == "significant_shift"


def test_k2_near_zero_for_normal_residuals():
    rng = np.random.RandomState(42)
    residuals = rng.normal(loc=0.0, scale=1.0, size=200)
    out = k2_score(residuals)
    assert out["k2_n"] == 200
    assert out["k2_pvalue"] >= 0.05
    assert out["k2_interpretation"] == "residuals_look_normal"


def test_k2_high_for_skewed_residuals():
    rng = np.random.RandomState(42)
    residuals = rng.exponential(scale=2.0, size=200)  # strongly right-skewed
    out = k2_score(residuals)
    assert out["k2"] > 5.0
    assert out["k2_pvalue"] < 0.05
    assert out["k2_interpretation"] == "residuals_non_normal"


def test_r2_perfect_prediction():
    """Bonus metric — R² is not CONTEXT K2."""
    actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert r2_score(actual, actual) == 1.0
    partial = actual + 0.5
    r2 = r2_score(actual, partial)
    assert 0.0 < r2 < 1.0


def test_all_metrics_computed_only_on_test_months():
    train_raw, test_raw, _, _, _, forecast = _trained()
    metrics = evaluate(
        test_raw[TARGET_COL], forecast["predicted"], train_revenue=train_raw[TARGET_COL]
    )
    assert metrics["n_test_months"] == 24
    assert len(test_raw) == 24
    assert "psi" in metrics
    assert "k2" in metrics
    assert "k2_pvalue" in metrics
    note = metrics["k2_note"].lower()
    assert "d'agostino" in note or "dagostino" in note or "residual" in note
    assert "bonus" in note or "r²" in note or "r2" in note


def test_forecast_plot_written_for_24_test_months(tmp_path: Path):
    _, test_raw, _, _, _, forecast = _trained()
    metrics = evaluate(test_raw[TARGET_COL], forecast["predicted"])
    out = tmp_path / "sales_forecast.png"
    plot_forecast(test_raw["month"], test_raw[TARGET_COL], forecast, out, metrics=metrics)
    assert out.exists() and out.stat().st_size > 0


def test_decomposition_matches_healthcore_seasonality_pattern():
    base = add_calendar_features(clean_sales(load_sales()))
    decomp = decompose_series(base)
    seas = decomp.dropna(subset=["seasonal"]).groupby("month_num")["seasonal"].mean()
    peak = set(seas.nlargest(3).index.tolist())
    trough = set(seas.nsmallest(3).index.tolist())
    assert peak & {10, 11, 12}, f"expected Oct–Dec among peaks, got {peak}"
    assert trough & {7, 8}, f"expected Jul–Aug among troughs, got {trough}"
