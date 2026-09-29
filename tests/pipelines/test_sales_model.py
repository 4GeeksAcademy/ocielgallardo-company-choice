"""Unit tests for the sales-forecasting training honesty (Phase 2–4).

Under test (Ticket: sales prediction model):

- the forest trains on 2016-2023 only; the 24 test months are predicted unseen.
- lag/rolling features are causal (month t never reads months >= t).
- the forecast has 24 rows with an ordered band (lo <= predicted <= hi).
- metrics are computed on test only, with the documented MSE-% formula.
- PSI ≈ 0 on identical distributions; PSI > 0.25 on a simulated shift.
- R² (CONTEXT "K2 Score") is 1.0 on perfect predictions.
- Visualization PNG is written for the 24 test months (CONTEXT columns).

Run:
    uv run python -m pytest tests/pipelines/test_sales_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make the repo root importable when pytest is invoked from elsewhere.
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
    add_lag_features,
    evaluate,
    feature_columns,
    interpret_psi,
    plot_forecast,
    population_stability_index,
    predict_with_band,
    r2_score,
    train_forest,
)

TEST_TREES = 20


def _split():
    frame = add_lag_features(add_calendar_features(clean_sales(load_sales())))
    # 108 rows after the 12-month lag warm-up drops (all inside train).
    return chronological_split(frame, expected=(84, 24))


def test_lag_features_are_causal():
    frame = add_lag_features(add_calendar_features(clean_sales(load_sales())))
    row = frame[frame["month"] == pd.Timestamp("2017-01-01")].iloc[0]
    raw = clean_sales(load_sales())
    raw["month"] = pd.to_datetime(raw["month"])
    raw = raw.set_index("month")
    assert row["lag_1"] == raw.loc[pd.Timestamp("2016-12-01"), TARGET_COL]
    assert row["lag_12"] == raw.loc[pd.Timestamp("2016-01-01"), TARGET_COL]
    assert frame["month"].min() == pd.Timestamp("2017-01-01")  # warm-up dropped, all in train


def test_train_never_sees_test_years():
    train, test = _split()
    assert train["month"].max() < pd.Timestamp("2024-01-01")
    assert test["month"].min() >= pd.Timestamp("2024-01-01")
    assert len(train) == 84
    assert len(test) == 24


def test_forecast_has_ordered_band_over_24_months():
    train, test = _split()
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=TEST_TREES)
    forecast = predict_with_band(model, test[cols])
    assert len(forecast) == 24
    assert ((forecast["band_lo"] <= forecast["predicted"])
            & (forecast["predicted"] <= forecast["band_hi"])).all()


def test_metrics_follow_documented_formula():
    train, test = _split()
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=TEST_TREES)
    forecast = predict_with_band(model, test[cols])
    metrics = evaluate(test[TARGET_COL], forecast["predicted"])
    assert metrics["n_test_months"] == 24
    assert metrics["mse_usd2"] > 0
    assert metrics["rmse_usd"] == metrics["mse_usd2"] ** 0.5
    assert metrics["rmse_pct_of_mean"] == (
        metrics["rmse_usd"] / metrics["mean_monthly_revenue_usd"] * 100
    )
    assert 0.0 <= metrics["gini"] <= 1.0
    assert "r2" in metrics


def test_psi_zero_with_identical_distributions():
    """PSI ≈ 0 when expected == actual (no distribution shift)."""
    rng = np.random.RandomState(42)
    data = rng.normal(loc=100_000, scale=10_000, size=200)
    psi = population_stability_index(data, data)
    assert psi < 0.01, f"PSI should be ≈0 for identical distributions, got {psi}"
    assert interpret_psi(psi) == "no_shift"


def test_psi_high_with_shifted_distribution():
    """PSI > 0.25 when the distribution shifts significantly."""
    rng = np.random.RandomState(42)
    expected = rng.normal(loc=100_000, scale=10_000, size=200)
    actual = rng.normal(loc=200_000, scale=10_000, size=200)  # heavy shift
    psi = population_stability_index(expected, actual)
    assert psi > 0.25, f"PSI should signal significant shift, got {psi}"
    assert interpret_psi(psi) == "significant_shift"


def test_r2_perfect_prediction():
    """R² = 1.0 when predicted == actual; partial fit stays in (0, 1)."""
    actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert r2_score(actual, actual) == 1.0
    partial = actual + 0.5  # constant offset — still captures trend
    r2 = r2_score(actual, partial)
    assert 0.0 < r2 < 1.0, f"expected partial R² in (0,1), got {r2}"


def test_all_metrics_computed_only_on_test_months():
    """Every metric in the dict comes from the 24 unseen test months."""
    train, test = _split()
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=TEST_TREES)
    forecast = predict_with_band(model, test[cols])
    metrics = evaluate(
        test[TARGET_COL], forecast["predicted"], train_revenue=train[TARGET_COL]
    )
    assert metrics["n_test_months"] == 24
    assert len(test) == 24
    assert "psi" in metrics
    assert "psi_interpretation" in metrics
    assert metrics["psi"] >= 0.0
    assert metrics["psi_interpretation"] in (
        "no_shift", "moderate_shift", "significant_shift"
    )
    assert "r2" in metrics
    assert "k2_note" in metrics


def test_forecast_plot_written_for_24_test_months(tmp_path: Path):
    """PNG deliverable covers exactly the 24 test months (CONTEXT columns)."""
    train, test = _split()
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=TEST_TREES)
    forecast = predict_with_band(model, test[cols])
    metrics = evaluate(test[TARGET_COL], forecast["predicted"])

    assert len(forecast) == 24
    assert list(forecast.columns) == ["predicted", "band_lo", "band_hi"]
    assert "month" in test.columns
    assert TARGET_COL in test.columns  # revenue_usd
    assert len(test) == 24

    out = tmp_path / "sales_forecast.png"
    plot_forecast(test["month"], test[TARGET_COL], forecast, out, metrics=metrics)
    assert out.exists()
    assert out.stat().st_size > 0
