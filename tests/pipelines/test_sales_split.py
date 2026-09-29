"""Unit tests for the sales-forecasting 8/2-year split (Phase 1).

Honesty guarantees under test (Ticket: sales prediction model):

- train = first 8 years (2016-01..2023-12, 96 rows), test = last 2 years
  (2024-01..2025-12, 24 rows) — the model never sees the test years.
- strictly chronological boundary, no shared months.
- the scaler is fitted on train only (test statistics never leak in).
- any null/empty cell fails loudly instead of being silently imputed.

Run:
    python -m pytest tests/pipelines/test_sales_split.py
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
    FEATURE_COLS,
    apply_scaling,
    chronological_split,
    clean_sales,
    fit_scaler,
    load_sales,
)


def _clean_frame() -> pd.DataFrame:
    return clean_sales(load_sales())


def test_split_is_96_train_24_test_on_date_boundary():
    train, test = chronological_split(_clean_frame())
    assert len(train) == 96
    assert len(test) == 24
    assert str(train["month"].min().date()) == "2016-01-01"
    assert str(train["month"].max().date()) == "2023-12-01"
    assert str(test["month"].min().date()) == "2024-01-01"
    assert str(test["month"].max().date()) == "2025-12-01"


def test_no_month_leaks_between_train_and_test():
    train, test = chronological_split(_clean_frame())
    assert train["month"].max() < test["month"].min()
    assert set(train["month"]).isdisjoint(set(test["month"]))


def test_scaler_is_fitted_on_train_only():
    frame = _clean_frame()
    train, test = chronological_split(frame)
    params = fit_scaler(train)
    # Scaler statistics must equal the TRAIN statistics, not the full data.
    for col in FEATURE_COLS:
        assert params[col]["mean"] == train[col].mean()
    # Train scaled features are centered; test scaled features are not forced to be.
    train_s, test_s = apply_scaling(train, test, params)
    for col in FEATURE_COLS:
        assert abs(train_s[f"{col}_scaled"].mean()) < 1e-9
    assert test_s[[f"{c}_scaled" for c in FEATURE_COLS]].notna().all().all()


def test_null_cell_fails_loudly():
    frame = load_sales()
    frame.loc[0, "revenue_usd"] = ""
    try:
        clean_sales(frame)
    except ValueError as exc:
        assert "null/empty" in str(exc)
    else:
        raise AssertionError("clean_sales tolerated a null cell")
