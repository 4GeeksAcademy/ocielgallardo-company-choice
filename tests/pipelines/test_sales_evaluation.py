"""Unit tests for formal temporal evaluation (academy rubric).

Covers: ≥5 chronological TimeSeriesSplit folds, lag-safe windows, MAE+RMSE,
stability mean±std, and diagnostic/recommendation mapping.

Run:
    uv run python -m pytest tests/pipelines/test_sales_evaluation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.evaluate_sales_model import (  # noqa: E402
    CV_GAP,
    CV_N_SPLITS,
    CV_TEST_SIZE,
    assert_folds_chronological,
    diagnose_fit,
    fold_metrics,
    iter_temporal_splits,
    learning_curve_rows,
    recommend_action,
    signed_bias,
    summarize_stability,
    temporal_cv_folds,
)
from scripts.prepare_sales_data import (  # noqa: E402
    add_calendar_features,
    chronological_split,
    clean_sales,
    load_sales,
)

TEST_TREES = 15


def _train_block() -> pd.DataFrame:
    base = add_calendar_features(clean_sales(load_sales()))
    train, test = chronological_split(base, expected=(96, 24))
    assert len(test) == 24
    return train


def test_signed_bias_positive_means_overestimation():
    actual = pd.Series([100.0, 100.0, 100.0])
    predicted = pd.Series([110.0, 120.0, 130.0])
    out = signed_bias(actual, predicted)
    assert out["mean_bias_usd"] > 0
    assert out["pct_months_underestimated"] == 0.0


def test_signed_bias_negative_means_underestimation():
    actual = pd.Series([100.0, 100.0, 100.0])
    predicted = pd.Series([90.0, 80.0, 70.0])
    out = signed_bias(actual, predicted)
    assert out["mean_bias_usd"] < 0
    assert out["pct_months_underestimated"] == 100.0


def test_fold_metrics_include_mae_and_rmse():
    actual = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])
    predicted = actual - 5.0
    metrics = fold_metrics(actual, predicted)
    assert metrics["mae_usd"] == 5.0
    assert metrics["rmse_usd"] == 5.0
    assert metrics["mean_bias_usd"] < 0
    assert metrics["pct_months_underestimated"] == 100.0
    assert metrics["n_months"] == 8


def test_learning_curve_sizes_increase_and_validation_is_future():
    curve = learning_curve_rows(_train_block(), n_estimators=TEST_TREES)
    assert len(curve) >= 2
    assert curve["n_train_raw"].is_monotonic_increasing
    assert curve["val_start"].nunique() == 1
    assert curve["val_end"].nunique() == 1
    for _, row in curve.iterrows():
        assert pd.Timestamp(row["train_end"]) < pd.Timestamp(row["val_start"])
        assert int(row["n_val"]) == 24
        assert int(row["gap_months"]) >= CV_GAP
        assert np.isfinite(row["val_rmse_pct"])
        assert np.isfinite(row["val_mae_pct"])
        assert row["train_mae_usd"] >= 0
        assert row["val_mae_usd"] >= 0


def test_temporal_cv_preserves_chronological_fold_order():
    """Academy: no later-fold index appears before an earlier fold's indices."""
    assert CV_N_SPLITS >= 5
    folds = assert_folds_chronological(96)
    assert len(folds) >= 5
    prev_val_max = -1
    for train_idx, val_idx in folds:
        assert np.all(np.diff(train_idx) > 0)
        assert np.all(np.diff(val_idx) > 0)
        assert train_idx.max() < val_idx.min()
        assert val_idx.min() > prev_val_max
        prev_val_max = int(val_idx.max())


def test_timeseries_split_has_no_shuffle_and_enforces_gap():
    n = 96
    for _fold_id, train_idx, val_idx in iter_temporal_splits(n):
        assert train_idx.max() < val_idx.min()
        assert val_idx.min() - train_idx.max() - 1 >= CV_GAP
        assert np.all(np.diff(train_idx) > 0)
        assert np.all(np.diff(val_idx) > 0)


def test_temporal_cv_folds_at_least_five_and_respect_gap():
    train = _train_block()
    cv = temporal_cv_folds(train, n_estimators=TEST_TREES)
    assert len(cv) >= 5
    assert len(cv) == CV_N_SPLITS
    sealed_start = pd.Timestamp("2024-01-01")
    prev_val_end = pd.Timestamp("1900-01-01")
    for _, row in cv.iterrows():
        assert pd.Timestamp(row["val_end"]) < sealed_start
        assert int(row["gap_months"]) >= CV_GAP
        assert pd.Timestamp(row["train_end"]) < pd.Timestamp(row["val_start"])
        assert int(row["n_val"]) == CV_TEST_SIZE
        assert pd.Timestamp(row["val_start"]) > prev_val_end
        prev_val_end = pd.Timestamp(row["val_end"])
        assert np.isfinite(row["val_mae_usd"])
        assert np.isfinite(row["val_rmse_usd"])


def test_summarize_stability_reports_mean_std_for_mae_and_rmse():
    fake = pd.DataFrame({
        "val_rmse_pct": [5.0, 6.0, 7.0],
        "val_rmse_usd": [1.0, 2.0, 3.0],
        "val_mae_pct": [4.0, 5.0, 6.0],
        "val_mae_usd": [0.5, 1.0, 1.5],
        "train_rmse_pct": [1.0, 1.0, 1.0],
        "train_mae_pct": [0.8, 0.8, 0.8],
        "val_gini": [0.8, 0.85, 0.9],
        "val_mean_bias_pct": [-1.0, 0.0, 1.0],
        "val_pct_underestimated": [40.0, 50.0, 60.0],
        "gap_rmse_pct": [1.0, 2.0, 3.0],
        "gap_mae_pct": [0.5, 1.0, 1.5],
    })
    summary = summarize_stability(fake)
    assert summary["val_rmse_pct"]["mean"] == 6.0
    assert summary["val_mae_pct"]["mean"] == 5.0
    assert summary["val_rmse_pct"]["std"] > 0
    assert summary["val_mae_usd"]["min"] == 0.5


def _stability_stub(**overrides):
    base = {
        "val_rmse_pct": {"mean": 6.0, "std": 0.3, "min": 5.5, "max": 6.5},
        "val_mean_bias_pct": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
        "val_pct_underestimated": {"mean": 50.0, "std": 0.0, "min": 50.0, "max": 50.0},
        "val_rmse_usd": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
        "val_mae_usd": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
        "val_mae_pct": {"mean": 5.0, "std": 0.0, "min": 5.0, "max": 5.0},
        "val_gini": {"mean": 0.5, "std": 0.0, "min": 0.5, "max": 0.5},
        "gap_rmse_pct": {"mean": 1.0, "std": 0.0, "min": 1.0, "max": 1.0},
    }
    base.update(overrides)
    return base


def test_diagnose_underfitting_pattern():
    curve = pd.DataFrame({
        "train_rmse_pct": [14.0, 13.5, 13.0],
        "val_rmse_pct": [15.0, 14.5, 14.0],
        "train_mae_pct": [12.0, 11.5, 11.0],
        "val_mae_pct": [13.0, 12.5, 12.0],
        "gap_rmse_pct": [1.0, 1.0, 1.0],
    })
    stability = _stability_stub(
        val_rmse_pct={"mean": 14.5, "std": 0.5, "min": 14.0, "max": 15.0},
    )
    diag = diagnose_fit(curve, stability)
    assert diag["fit_label"] == "underfitting"
    rec = recommend_action(diag, stability)
    assert "max_depth" in rec["action"]
    assert "is_flu_season" in rec["action"]


def test_diagnose_overfitting_pattern():
    curve = pd.DataFrame({
        "train_rmse_pct": [2.0, 1.5, 1.0],
        "val_rmse_pct": [10.0, 9.5, 9.0],
        "train_mae_pct": [1.5, 1.2, 0.9],
        "val_mae_pct": [8.0, 7.5, 7.0],
        "gap_rmse_pct": [8.0, 8.0, 8.0],
    })
    stability = _stability_stub(
        val_rmse_pct={"mean": 9.5, "std": 0.4, "min": 9.0, "max": 10.0},
        val_mean_bias_pct={"mean": -2.0, "std": 0.0, "min": -2.0, "max": -2.0},
        val_pct_underestimated={"mean": 60.0, "std": 0.0, "min": 60.0, "max": 60.0},
        gap_rmse_pct={"mean": 8.0, "std": 0.0, "min": 8.0, "max": 8.0},
    )
    diag = diagnose_fit(curve, stability)
    assert diag["fit_label"] == "overfitting"
    rec = recommend_action(diag, stability)
    assert "max_depth=6" in rec["action"]
    assert "min_samples_leaf=3" in rec["action"]
    assert "underestimation" in rec["business_note"].lower()


def test_diagnose_reasonably_well_fitted_pattern():
    curve = pd.DataFrame({
        "train_rmse_pct": [5.5, 5.0, 4.8],
        "val_rmse_pct": [6.5, 6.0, 5.9],
        "train_mae_pct": [4.5, 4.0, 3.8],
        "val_mae_pct": [5.5, 5.0, 4.9],
        "gap_rmse_pct": [1.0, 1.0, 1.1],
    })
    stability = _stability_stub(
        val_mean_bias_pct={"mean": 0.2, "std": 0.0, "min": 0.2, "max": 0.2},
        val_pct_underestimated={"mean": 48.0, "std": 0.0, "min": 48.0, "max": 48.0},
    )
    diag = diagnose_fit(curve, stability)
    assert diag["fit_label"] == "reasonably_well_fitted"
    assert diag["stability_label"] == "stable"
    rec = recommend_action(diag, stability)
    assert "Do not increase model complexity" in rec["action"]
