"""Sales data preparation — Phase 1 (Ticket: sales prediction model).

Standalone process — run from the repo root with::

    python scripts/prepare_sales_data.py

Pipeline (in this order — the order is the honesty guarantee)::

    1. load  data/raw/healthcore_sales.csv (120 consolidated months)
    2. clean (normalize blanks/null tokens, validate types + business rules,
       fail loudly on any null — never silently impute from the future)
    3. split chronologically BEFORE any statistics: train 2016-01..2023-12
       (96 rows), test 2024-01..2025-12 (24 rows). The model never sees test.
    4. scale numeric features with z-score parameters FIT ON TRAIN ONLY, then
       transform both sets with those same parameters (same math as
       StandardScaler; dependency-free so Phase 1 runs in the base env —
       scikit-learn arrives in Phase 2 with the model).

Artifacts (gitignored runtime data)::

    data/process/sales_forecasting/train_scaled.csv
    data/process/sales_forecasting/test_scaled.csv
    data/process/sales_forecasting/scaler.json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import pandas as pd

logger = logging.getLogger("prepare_sales_data")

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = REPO_ROOT / "data" / "raw" / "healthcore_sales.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "process" / "sales_forecasting"

TARGET_COL = "revenue_usd"
NUMERIC_COLS = ["revenue_usd", "visits_count", "avg_revenue_per_visit_usd"]
# Columns the scaler learns (target excluded — it is what we predict).
FEATURE_COLS = ["visits_count", "avg_revenue_per_visit_usd"]

TRAIN_START = "2016-01-01"
TRAIN_END = "2023-12-01"
TEST_START = "2024-01-01"
TEST_END = "2025-12-01"

NULL_TOKENS = {"", "null", "none", "nan", "na", "n/a", "nat", "?", "-"}
CALENDAR_COLS = ["year", "month_sin", "month_cos"]


def load_sales(path: Path = SOURCE_CSV) -> pd.DataFrame:
    """Read the raw CSV keeping everything as text for honest validation."""
    if not path.exists():
        raise FileNotFoundError(f"sales dataset not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    logger.info("loaded %d rows from %s", len(frame), path)
    return frame


def clean_sales(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize blanks/null tokens and enforce types + business rules.

    Raises:
        ValueError: on any null/empty cell, bad type, non-positive revenue,
            missing month, or non-consolidated row — with row/column detail.
    """
    frame = frame.copy()
    expected = ["month", "revenue_usd", "visits_count", "avg_revenue_per_visit_usd", "region"]
    if list(frame.columns) != expected:
        raise ValueError(f"unexpected columns {list(frame.columns)}, expected {expected}")

    n_before = len(frame)

    # 1. Normalize blanks and null tokens to real NaN.
    for col in frame.columns:
        frame[col] = frame[col].map(
            lambda v: float("nan") if str(v).strip().lower() in NULL_TOKENS else str(v).strip()
        )
    nulls = frame[frame.isna().any(axis=1)]
    if not nulls.empty:
        detail = "; ".join(
            f"row {i} ({frame.loc[i, 'month'] if 'month' in frame.columns else '?'}): "
            + ", ".join(c for c in frame.columns if pd.isna(frame.loc[i, c]))
            for i in nulls.index[:10]
        )
        raise ValueError(f"{len(nulls)} rows with null/empty cells — refusing to impute: {detail}")

    # 2. Types.
    try:
        frame["month"] = pd.to_datetime(frame["month"], format="%Y-%m-%d")
    except Exception as exc:
        raise ValueError(f"bad month format (expected YYYY-MM-01): {exc}") from exc
    for col in NUMERIC_COLS:
        try:
            frame[col] = pd.to_numeric(frame[col])
        except Exception as exc:
            raise ValueError(f"non-numeric value in column '{col}': {exc}") from exc
    if frame[NUMERIC_COLS].isna().any().any():
        raise ValueError("numeric conversion produced NaN — refusing to continue")

    # 3. Business rules from CONTEXT.
    if (frame["region"] != "consolidated").any():
        raise ValueError("only 'consolidated' rows are in scope for this model")
    if (frame[TARGET_COL] <= 0).any():
        bad = frame[frame[TARGET_COL] <= 0]["month"].astype(str).tolist()
        raise ValueError(f"non-positive revenue_usd in months: {bad}")

    # 4. Continuity: every month 2016-01..2025-12 exactly once.
    frame = frame.sort_values("month").reset_index(drop=True)
    expected_months = pd.date_range(TRAIN_START, TEST_END, freq="MS")
    actual_months = pd.DatetimeIndex(frame["month"])
    if len(frame) != len(expected_months) or (actual_months != expected_months).any():
        missing = expected_months.difference(actual_months).strftime("%Y-%m").tolist()
        dupes = actual_months[actual_months.duplicated()].strftime("%Y-%m").tolist()
        raise ValueError(f"month continuity broken — missing: {missing}, duplicated: {dupes}")

    logger.info("cleaned %d rows (dropped %d), 0 nulls tolerated", len(frame), n_before - len(frame))
    return frame


def add_calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive causal calendar features (month is known upfront, no leakage)."""
    frame = frame.copy()
    frame["year"] = frame["month"].dt.year
    month_num = frame["month"].dt.month
    frame["month_sin"] = (2 * math.pi * month_num / 12).map(math.sin)
    frame["month_cos"] = (2 * math.pi * month_num / 12).map(math.cos)
    return frame


def chronological_split(frame: pd.DataFrame,
                          expected: tuple[int, int] = (96, 24)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split 8 years train / 2 years test on the date boundary.

    Must run BEFORE any feature statistics so the test years stay unseen.
    ``expected`` is (96, 24) on the raw series; callers that already dropped
    warm-up rows (e.g. lag features) pass their own counts — the boundary
    and no-overlap guarantees always hold.
    """
    train = frame[frame["month"] <= TRAIN_END].reset_index(drop=True)
    test = frame[(frame["month"] >= TEST_START) & (frame["month"] <= TEST_END)].reset_index(drop=True)
    if (len(train), len(test)) != expected:
        raise ValueError(f"expected {expected[0]}/{expected[1]} split, got {len(train)}/{len(test)}")
    if train["month"].max() >= test["month"].min():
        raise ValueError("train/test months overlap — chronological boundary broken")
    if set(train["month"]) & set(test["month"]):
        raise ValueError("a test month leaked into train")
    logger.info("split: train %s..%s (%d), test %s..%s (%d)",
                train["month"].min().date(), train["month"].max().date(), len(train),
                test["month"].min().date(), test["month"].max().date(), len(test))
    return train, test


def fit_scaler(train: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Fit z-score parameters on TRAIN features only (never on test).

    Same math as ``StandardScaler`` (population std, ``ddof=0``) without the
    sklearn dependency — scikit-learn arrives in Phase 2 with the model.
    """
    params = {
        col: {"mean": float(train[col].mean()), "scale": float(train[col].std(ddof=0))}
        for col in FEATURE_COLS
    }
    for col, p in params.items():
        if p["scale"] == 0:
            raise ValueError(f"zero variance in train column '{col}' — cannot scale")
    logger.info("scaler fitted on train: %s",
                {c: {k: round(v, 4) for k, v in p.items()} for c, p in params.items()})
    return params


def apply_scaling(train: pd.DataFrame, test: pd.DataFrame,
                  params: dict[str, dict[str, float]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Transform both sets with the train-fitted parameters (target untouched)."""
    train = train.copy()
    test = test.copy()
    for col in FEATURE_COLS:
        mean, scale = params[col]["mean"], params[col]["scale"]
        train[f"{col}_scaled"] = (train[col] - mean) / scale
        test[f"{col}_scaled"] = (test[col] - mean) / scale
    return train, test


def main(output_dir: Path = OUTPUT_DIR) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        frame = clean_sales(load_sales())
        frame = add_calendar_features(frame)
        train, test = chronological_split(frame)
        scaler = fit_scaler(train)
        train, test = apply_scaling(train, test, scaler)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    train.to_csv(output_dir / "train_scaled.csv", index=False)
    test.to_csv(output_dir / "test_scaled.csv", index=False)
    (output_dir / "scaler.json").write_text(
        json.dumps({"feature_cols": FEATURE_COLS, "params": scaler}, indent=2),
        encoding="utf-8",
    )
    logger.info("artifacts written to %s (train=%d, test=%d)", output_dir, len(train), len(test))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare HealthCore sales data (Phase 1).")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    raise SystemExit(main(output_dir=parser.parse_args().output_dir))
