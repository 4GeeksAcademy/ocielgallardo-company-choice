"""Unit tests for the sales-forecasting training honesty (Phase 2).

Under test (Ticket: sales prediction model):

- the forest trains on 2016-2023 only; the 24 test months are predicted unseen.
- lag/rolling features are causal (month t never reads months >= t).
- the forecast has 24 rows with an ordered band (lo <= predicted <= hi).
- metrics are computed on test only, with the documented MSE-% formula.

Run:
    uv run python -m pytest tests/pipelines/test_sales_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

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
    predict_with_band,
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
