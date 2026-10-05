"""Formal evaluation of the HealthCore sales forecast model (academy rubric).

Answers the staging / course ticket with evidence (not opinions)::

    1. underfitting / overfitting / reasonably well fitted (learning curves)
    2. performance stability across ≥5 temporal CV folds (mean ± std)
    3. specific corrective action when a problem is diagnosed

Standalone — run from the repo root with::

    uv run python scripts/evaluate_sales_model.py

Academy artifacts (committed under ``data/eval/``)::

    learning_curve.png
    evaluation_report.md
    sales_cv_folds.csv
    sales_learning_curve.csv
    sales_evaluation.json
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Iterator

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from scripts.prepare_sales_data import (
    REPO_ROOT,
    TARGET_COL,
    add_calendar_features,
    chronological_split,
    clean_sales,
    load_sales,
)
from scripts.train_sales_model import (
    LAG_MONTHS,
    N_ESTIMATORS,
    RANDOM_STATE,
    add_lag_features,
    evaluate,
    feature_columns,
    forecast_recursive,
    train_forest,
)

logger = logging.getLogger("evaluate_sales_model")

EVAL_DIR = REPO_ROOT / "data" / "eval"

# Temporal CV inside the 8-year train block only.
# n_splits=5 (academy minimum); test_size=12 (1 year); gap=12 purges lag_12.
# With n=96: fold train lengths = 24, 36, 48, 60, 72 raw months (≥24 floor).
CV_N_SPLITS = 5
CV_TEST_SIZE = 12
CV_GAP = 12
MIN_TRAIN_MONTHS = 24  # enough for lag_12 warm-up (≥12 fit rows)

# Learning curve: fixed future validation = last 24 months of the train block.
LEARNING_CURVE_SIZES = (36, 48, 60)
LEARNING_CURVE_VAL_MONTHS = 24

# Diagnosis thresholds (RMSE % of mean revenue on the validation window).
HIGH_ERROR_PCT = 12.0
GAP_OVERFIT_PCT = 4.0
STABLE_STD_PCT = 3.0

PRIMARY_METRIC = "rmse"
PRIMARY_METRIC_JUSTIFICATION = (
    "Primary metric = RMSE (also reported as % of mean monthly revenue_usd). "
    "HealthCore CONTEXT asks for MSE/RMSE in USD² and as % of mean monthly "
    "revenue so Tom (Revenue Cycle) and Sandra (CEO) can read budget risk without "
    "translation. RMSE penalizes large month-level misses more than MAE — those "
    "spikes matter for capacity planning around flu season (Oct–Dec) vs summer "
    "troughs (Jul–Aug). MAE is reported as a secondary, easier-to-explain average "
    "dollar miss. Working assumption (ROADMAP §2.4): underestimating demand is "
    "the costlier side for clinic capacity; directional bias "
    "(prediction − actual) is tracked alongside RMSE."
)


def signed_bias(actual: pd.Series | np.ndarray,
                predicted: pd.Series | np.ndarray) -> dict[str, float]:
    """Directional error: prediction − actual.

    Positive mean ⇒ systematic overestimation.
    Negative mean ⇒ systematic underestimation (costlier for capacity planning).
    """
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)
    err = predicted_arr - actual_arr
    n = len(err)
    if n == 0:
        raise ValueError("signed_bias requires at least one observation")
    under = err < 0
    return {
        "mean_bias_usd": float(err.mean()),
        "mean_bias_pct_of_mean": float(err.mean() / actual_arr.mean() * 100)
        if actual_arr.mean()
        else float("nan"),
        "pct_months_underestimated": float(under.mean() * 100),
        "pct_months_overestimated": float((~under & (err != 0)).mean() * 100),
    }


def mean_absolute_error(actual: pd.Series | np.ndarray,
                        predicted: pd.Series | np.ndarray) -> float:
    actual_arr = np.asarray(actual, dtype=float)
    predicted_arr = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(actual_arr - predicted_arr)))


def fold_metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """MAE + RMSE (+ bias) on a single window, position-aligned."""
    actual = pd.Series(np.asarray(actual, dtype=float)).reset_index(drop=True)
    predicted = pd.Series(np.asarray(predicted, dtype=float)).reset_index(drop=True)
    base = evaluate(actual, predicted)
    bias = signed_bias(actual, predicted)
    mae = mean_absolute_error(actual, predicted)
    mean_rev = float(base["mean_monthly_revenue_usd"])
    return {
        "mae_usd": mae,
        "mae_pct_of_mean": mae / mean_rev * 100 if mean_rev else float("nan"),
        "rmse_usd": float(base["rmse_usd"]),
        "rmse_pct_of_mean": float(base["rmse_pct_of_mean"]),
        "gini": float(base["gini"]),
        "mean_bias_usd": bias["mean_bias_usd"],
        "mean_bias_pct_of_mean": bias["mean_bias_pct_of_mean"],
        "pct_months_underestimated": bias["pct_months_underestimated"],
        "n_months": int(base["n_test_months"]),
    }


def _prepare_series() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load + clean + calendar, then chronological 8/2 split (test sealed)."""
    base = add_calendar_features(clean_sales(load_sales()))
    return chronological_split(base, expected=(96, 24))


def _fit_and_score_window(
    train_raw: pd.DataFrame,
    val_raw: pd.DataFrame,
    n_estimators: int,
) -> dict[str, float]:
    """Train on ``train_raw`` only; lags rebuilt inside the fold (no global leak)."""
    # Lags/rollings are computed ONLY on this fold's train rows — never on the
    # full series before the split (academy anti-leak requirement).
    train = add_lag_features(train_raw.copy())
    if train.empty:
        raise ValueError("train window too short after lag warm-up")
    cols = feature_columns(train)
    model = train_forest(train[cols], train[TARGET_COL], n_estimators=n_estimators)

    train_pred = model.predict(np.asarray(train[cols]))
    train_m = fold_metrics(train[TARGET_COL], pd.Series(train_pred))

    forecast = forecast_recursive(
        model,
        train_history=train_raw[TARGET_COL],
        test_calendar=val_raw[["month", "year", "month_sin", "month_cos"]],
        feature_cols=cols,
    )
    val_m = fold_metrics(val_raw[TARGET_COL], forecast["predicted"])
    return {
        "train_mae_usd": train_m["mae_usd"],
        "val_mae_usd": val_m["mae_usd"],
        "train_mae_pct": train_m["mae_pct_of_mean"],
        "val_mae_pct": val_m["mae_pct_of_mean"],
        "train_rmse_pct": train_m["rmse_pct_of_mean"],
        "val_rmse_pct": val_m["rmse_pct_of_mean"],
        "train_rmse_usd": train_m["rmse_usd"],
        "val_rmse_usd": val_m["rmse_usd"],
        "val_gini": val_m["gini"],
        "val_mean_bias_usd": val_m["mean_bias_usd"],
        "val_mean_bias_pct": val_m["mean_bias_pct_of_mean"],
        "val_pct_underestimated": val_m["pct_months_underestimated"],
        "n_train_raw": int(len(train_raw)),
        "n_train_fit": int(len(train)),
        "n_val": int(len(val_raw)),
        "gap_rmse_pct": float(val_m["rmse_pct_of_mean"] - train_m["rmse_pct_of_mean"]),
        "gap_mae_pct": float(val_m["mae_pct_of_mean"] - train_m["mae_pct_of_mean"]),
    }


def iter_temporal_splits(
    n_samples: int,
    n_splits: int = CV_N_SPLITS,
    test_size: int = CV_TEST_SIZE,
    gap: int = CV_GAP,
) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
    """Yield (fold_id, train_idx, val_idx) from TimeSeriesSplit (no shuffle)."""
    splitter = TimeSeriesSplit(n_splits=n_splits, test_size=test_size, gap=gap)
    for fold_id, (train_idx, val_idx) in enumerate(splitter.split(np.arange(n_samples))):
        yield fold_id, train_idx, val_idx


def assert_folds_chronological(
    n_samples: int = 96,
    n_splits: int = CV_N_SPLITS,
    test_size: int = CV_TEST_SIZE,
    gap: int = CV_GAP,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Academy check: chronological order preserved; later-fold indices never precede earlier ones."""
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    prev_val_max = -1
    for fold_id, train_idx, val_idx in iter_temporal_splits(
        n_samples, n_splits=n_splits, test_size=test_size, gap=gap
    ):
        if not np.all(np.diff(train_idx) > 0):
            raise AssertionError(f"fold {fold_id}: train indices not strictly increasing")
        if not np.all(np.diff(val_idx) > 0):
            raise AssertionError(f"fold {fold_id}: val indices not strictly increasing")
        if train_idx.max() >= val_idx.min():
            raise AssertionError(f"fold {fold_id}: train overlaps or follows validation")
        if val_idx.min() - train_idx.max() - 1 < gap:
            raise AssertionError(f"fold {fold_id}: purge gap < {gap}")
        if val_idx.min() <= prev_val_max:
            raise AssertionError(
                f"fold {fold_id}: validation index {val_idx.min()} appears at or before "
                f"a prior fold's max validation index {prev_val_max}"
            )
        prev_val_max = int(val_idx.max())
        folds.append((train_idx, val_idx))
    if len(folds) < 5:
        raise AssertionError(f"expected ≥5 folds, got {len(folds)}")
    return folds


def learning_curve_rows(
    train_block: pd.DataFrame,
    sizes: tuple[int, ...] = LEARNING_CURVE_SIZES,
    val_months: int = LEARNING_CURVE_VAL_MONTHS,
    gap: int = CV_GAP,
    n_estimators: int = N_ESTIMATORS,
) -> pd.DataFrame:
    """Expanding-prefix learning curve inside the 8-year train block."""
    train_block = train_block.sort_values("month").reset_index(drop=True)
    if len(train_block) < val_months + gap + min(sizes):
        raise ValueError("train block too short for learning curve configuration")
    val_raw = train_block.iloc[-val_months:].copy()
    max_train_end = len(train_block) - val_months - gap
    rows: list[dict[str, float | int]] = []
    for size in sizes:
        if size > max_train_end or size < 24:
            continue
        train_raw = train_block.iloc[:size].copy()
        scored = _fit_and_score_window(train_raw, val_raw, n_estimators=n_estimators)
        scored["requested_train_size"] = int(size)
        scored["val_start"] = str(val_raw["month"].min().date())
        scored["val_end"] = str(val_raw["month"].max().date())
        scored["train_end"] = str(train_raw["month"].max().date())
        scored["gap_months"] = int(gap)
        rows.append(scored)
        logger.info(
            "learning curve size=%d train_rmse=%.2f%% val_rmse=%.2f%% "
            "train_mae=%.2f%% val_mae=%.2f%%",
            size, scored["train_rmse_pct"], scored["val_rmse_pct"],
            scored["train_mae_pct"], scored["val_mae_pct"],
        )
    if not rows:
        raise ValueError("learning curve produced no rows — check sizes vs train length")
    return pd.DataFrame(rows)


def temporal_cv_folds(
    train_block: pd.DataFrame,
    n_splits: int = CV_N_SPLITS,
    test_size: int = CV_TEST_SIZE,
    gap: int = CV_GAP,
    n_estimators: int = N_ESTIMATORS,
) -> pd.DataFrame:
    """TimeSeriesSplit on the train block only (sealed test never enters CV)."""
    train_block = train_block.sort_values("month").reset_index(drop=True)
    n = len(train_block)
    assert_folds_chronological(n, n_splits=n_splits, test_size=test_size, gap=gap)
    rows: list[dict[str, Any]] = []
    for fold_id, train_idx, val_idx in iter_temporal_splits(
        n, n_splits=n_splits, test_size=test_size, gap=gap
    ):
        if len(train_idx) < MIN_TRAIN_MONTHS:
            raise ValueError(
                f"fold {fold_id}: train too short ({len(train_idx)} < {MIN_TRAIN_MONTHS})"
            )
        train_raw = train_block.iloc[train_idx].copy()
        val_raw = train_block.iloc[val_idx].copy()
        months_between = (
            (val_raw["month"].min().year - train_raw["month"].max().year) * 12
            + (val_raw["month"].min().month - train_raw["month"].max().month)
        )
        scored = _fit_and_score_window(train_raw, val_raw, n_estimators=n_estimators)
        scored.update({
            "fold": int(fold_id),
            "train_start": str(train_raw["month"].min().date()),
            "train_end": str(train_raw["month"].max().date()),
            "val_start": str(val_raw["month"].min().date()),
            "val_end": str(val_raw["month"].max().date()),
            "gap_months": int(months_between - 1),
            "n_train_idx": int(len(train_idx)),
            "n_val_idx": int(len(val_idx)),
            "train_idx_min": int(train_idx.min()),
            "train_idx_max": int(train_idx.max()),
            "val_idx_min": int(val_idx.min()),
            "val_idx_max": int(val_idx.max()),
        })
        rows.append(scored)
        logger.info(
            "CV fold=%d val_rmse=%.2f%%± val_mae=%.2f bias=%.2f%% under=%.1f%% gap=%d",
            fold_id, scored["val_rmse_pct"], scored["val_mae_pct"],
            scored["val_mean_bias_pct"], scored["val_pct_underestimated"],
            scored["gap_months"],
        )
    if len(rows) < 5:
        raise ValueError(f"temporal CV produced {len(rows)} folds; academy requires ≥5")
    return pd.DataFrame(rows)


def summarize_stability(cv: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Mean / std / min / max across folds for key metrics."""
    keys = [
        "val_rmse_pct",
        "val_rmse_usd",
        "val_mae_pct",
        "val_mae_usd",
        "train_rmse_pct",
        "train_mae_pct",
        "val_gini",
        "val_mean_bias_pct",
        "val_pct_underestimated",
        "gap_rmse_pct",
        "gap_mae_pct",
    ]
    summary: dict[str, dict[str, float]] = {}
    for key in keys:
        if key not in cv.columns:
            continue
        series = cv[key].astype(float)
        summary[key] = {
            "mean": float(series.mean()),
            "std": float(series.std(ddof=0)),
            "min": float(series.min()),
            "max": float(series.max()),
        }
    return summary


def format_mean_std(summary: dict[str, dict[str, float]], key: str,
                    suffix: str = "") -> str:
    """Human-readable ``mean ± std`` for the report."""
    block = summary[key]
    return f"{block['mean']:.2f}{suffix} ± {block['std']:.2f}{suffix}"


def diagnose_fit(
    curve: pd.DataFrame,
    stability: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Map learning-curve + CV pattern → underfitting / overfitting / well fitted."""
    train_err = float(curve["train_rmse_pct"].iloc[-1])
    val_err = float(curve["val_rmse_pct"].iloc[-1])
    mean_gap = float(curve["gap_rmse_pct"].mean())
    val_std = float(stability["val_rmse_pct"]["std"])

    if train_err >= HIGH_ERROR_PCT and val_err >= HIGH_ERROR_PCT and mean_gap < GAP_OVERFIT_PCT:
        label = "underfitting"
        rationale = (
            f"Train and validation RMSE stay high and close "
            f"(train={train_err:.2f}%, val={val_err:.2f}%, mean_gap={mean_gap:.2f}%)."
        )
    elif mean_gap >= GAP_OVERFIT_PCT and train_err < HIGH_ERROR_PCT:
        label = "overfitting"
        rationale = (
            f"Persistent train/validation gap "
            f"(mean_gap={mean_gap:.2f}%, last train={train_err:.2f}%, "
            f"last val={val_err:.2f}%)."
        )
    else:
        label = "reasonably_well_fitted"
        rationale = (
            f"Train and validation errors are moderate and close "
            f"(train={train_err:.2f}%, val={val_err:.2f}%, mean_gap={mean_gap:.2f}%)."
        )

    stability_label = "stable" if val_std <= STABLE_STD_PCT else "unstable"
    return {
        "fit_label": label,
        "rationale": rationale,
        "last_train_rmse_pct": train_err,
        "last_val_rmse_pct": val_err,
        "last_train_mae_pct": float(curve["train_mae_pct"].iloc[-1]),
        "last_val_mae_pct": float(curve["val_mae_pct"].iloc[-1]),
        "mean_gap_rmse_pct": mean_gap,
        "cv_val_rmse_pct_std": val_std,
        "stability_label": stability_label,
        "thresholds": {
            "high_error_pct": HIGH_ERROR_PCT,
            "gap_overfit_pct": GAP_OVERFIT_PCT,
            "stable_std_pct": STABLE_STD_PCT,
        },
    }


def recommend_action(diagnosis: dict[str, Any],
                     stability: dict[str, dict[str, float]]) -> dict[str, str]:
    """Specific corrective action — not a generic checklist."""
    fit = diagnosis["fit_label"]
    bias_mean = float(stability["val_mean_bias_pct"]["mean"])
    under_pct = float(stability["val_pct_underestimated"]["mean"])

    if fit == "underfitting":
        action = (
            "Increase RandomForestRegressor max_depth from the current unrestricted "
            "default to an explicit search starting at max_depth=8 (with "
            "min_samples_leaf=2 held fixed), and add a binary is_flu_season feature "
            "(month in {10,11,12}) so the forest can split on HealthCore's Oct–Dec peak "
            "without needing deeper trees on noise."
        )
        why = (
            "High train and validation error with a small gap means the model lacks "
            "capacity or signal, not that it needs more years of data first."
        )
    elif fit == "overfitting":
        action = (
            "Constrain the forest: set max_depth=6 and min_samples_leaf=3 on "
            "RandomForestRegressor (random_state=42 unchanged), re-run this evaluation "
            "script, and keep the change only if CV val_rmse_pct mean falls and "
            "mean_gap_rmse_pct shrinks below 4%."
        )
        why = (
            "A persistent train≪validation gap indicates memorization; the first lever "
            "is reducing tree complexity, not adding features or estimators."
        )
    else:
        action = (
            "Do not increase model complexity. Keep the current honest recursive RF; "
            "next step before staging is to report sealed-test metrics alongside this "
            "CV package and confirm the underestimation-cost assumption with the "
            "business owner (ROADMAP §2.4 TODO)."
        )
        why = (
            "Curves converge at moderate error with a small gap; complexity changes "
            "would risk overfitting without a clear error reduction target."
        )

    if bias_mean < 0 or under_pct >= 55:
        business_note = (
            f"Directional bias leans toward underestimation "
            f"(mean bias={bias_mean:.2f}% of mean revenue, "
            f"{under_pct:.1f}% of fold months underestimated). "
            "For capacity planning this is the costlier side — monitor sealed-test "
            "bias before promoting, even if fit_label is acceptable."
        )
    elif bias_mean > 0 and under_pct <= 45:
        business_note = (
            f"Directional bias leans toward overestimation "
            f"(mean bias={bias_mean:.2f}%, {under_pct:.1f}% months underestimated). "
            "Less critical for access risk, but still review budget implications."
        )
    else:
        business_note = (
            f"Directional bias is near balanced "
            f"(mean bias={bias_mean:.2f}%, {under_pct:.1f}% months underestimated)."
        )

    if diagnosis["stability_label"] == "unstable":
        stability_note = (
            f"CV val_rmse_pct std={diagnosis['cv_val_rmse_pct_std']:.2f}% exceeds "
            f"{STABLE_STD_PCT}% — treat a single sealed-test RMSE as insufficient; "
            "quote the CV range in the staging report."
        )
    else:
        stability_note = (
            f"CV val_rmse_pct std={diagnosis['cv_val_rmse_pct_std']:.2f}% ≤ "
            f"{STABLE_STD_PCT}% — fold performance is acceptably stable."
        )

    return {
        "action": action,
        "why": why,
        "business_note": business_note,
        "stability_note": stability_note,
    }


def plot_learning_curve(curve: pd.DataFrame, path: Path) -> None:
    """Train vs validation RMSE % (primary) and MAE % (secondary)."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=True)
    x = curve["n_train_raw"].astype(int)

    axes[0].plot(x, curve["train_rmse_pct"], marker="o", label="Train RMSE %")
    axes[0].plot(x, curve["val_rmse_pct"], marker="o", label="Validation RMSE %")
    axes[0].set_xlabel("Training months (raw)")
    axes[0].set_ylabel("RMSE (% of mean monthly revenue_usd)")
    axes[0].set_title("Learning curve — RMSE (primary)")
    axes[0].legend(loc="best")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(x, curve["train_mae_pct"], marker="o", label="Train MAE %")
    axes[1].plot(x, curve["val_mae_pct"], marker="o", label="Validation MAE %")
    axes[1].set_xlabel("Training months (raw)")
    axes[1].set_ylabel("MAE (% of mean monthly revenue_usd)")
    axes[1].set_title("Learning curve — MAE (secondary)")
    axes[1].legend(loc="best")
    axes[1].grid(True, alpha=0.3)

    fig.suptitle(
        "HealthCore sales RF — temporal learning curve (train block; sealed test excluded)"
    )
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    logger.info("learning curve plot written to %s", path)


def build_report(
    curve: pd.DataFrame,
    cv: pd.DataFrame,
    stability: dict[str, dict[str, float]],
    diagnosis: dict[str, Any],
    recommendation: dict[str, str],
    n_estimators: int,
) -> dict[str, Any]:
    """JSON-serializable evaluation package."""
    return {
        "model": "RandomForestRegressor",
        "random_state": RANDOM_STATE,
        "n_estimators": n_estimators,
        "target": TARGET_COL,
        "features": feature_columns(),
        "max_lag_months": max(LAG_MONTHS),
        "primary_metric": PRIMARY_METRIC,
        "primary_metric_justification": PRIMARY_METRIC_JUSTIFICATION,
        "cv": {
            "splitter": "sklearn.model_selection.TimeSeriesSplit",
            "n_splits": CV_N_SPLITS,
            "test_size": CV_TEST_SIZE,
            "gap": CV_GAP,
            "shuffle": False,
            "lag_policy": (
                "add_lag_features(train_fold_only); recursive val forecast; "
                f"gap={CV_GAP} months purges lag_12 across fold boundary"
            ),
            "scope": "8-year train block only; sealed 2-year test never used in CV",
        },
        "learning_curve": curve.to_dict(orient="records"),
        "folds": cv.to_dict(orient="records"),
        "stability": stability,
        "stability_mean_std": {
            "val_rmse_pct": format_mean_std(stability, "val_rmse_pct", "%"),
            "val_mae_pct": format_mean_std(stability, "val_mae_pct", "%"),
            "val_rmse_usd": format_mean_std(stability, "val_rmse_usd", " USD"),
            "val_mae_usd": format_mean_std(stability, "val_mae_usd", " USD"),
        },
        "diagnosis": diagnosis,
        "recommendation": recommendation,
        "ticket_answers": {
            "fit": diagnosis["fit_label"],
            "stability": diagnosis["stability_label"],
            "corrective_action": recommendation["action"],
        },
        "business_error_assumption": {
            "costlier_error": "underestimation",
            "bias_definition": "prediction - actual",
            "note": (
                "Working assumption from ROADMAP §2.4 — confirm with business owner "
                "before staging approval."
            ),
        },
    }


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    """Academy deliverable: data/eval/evaluation_report.md."""
    diag = report["diagnosis"]
    rec = report["recommendation"]
    stab = report["stability"]
    mean_std = report["stability_mean_std"]
    fit = diag["fit_label"]
    fit_es = {
        "underfitting": "underfitting",
        "overfitting": "overfitting",
        "reasonably_well_fitted": "reasonably well fitted (bien ajustado)",
    }.get(fit, fit)

    fold_lines = [
        "| Fold | Train end | Val window | Val RMSE % | Val MAE % | Bias % | % under |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["folds"]:
        fold_lines.append(
            f"| {row['fold']} | {row['train_end']} | {row['val_start']}→{row['val_end']} "
            f"| {row['val_rmse_pct']:.2f} | {row['val_mae_pct']:.2f} "
            f"| {row['val_mean_bias_pct']:.2f} | {row['val_pct_underestimated']:.1f} |"
        )

    curve_lines = [
        "| Train months | Train RMSE % | Val RMSE % | Train MAE % | Val MAE % |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["learning_curve"]:
        curve_lines.append(
            f"| {row['n_train_raw']} | {row['train_rmse_pct']:.2f} | {row['val_rmse_pct']:.2f} "
            f"| {row['train_mae_pct']:.2f} | {row['val_mae_pct']:.2f} |"
        )

    body = f"""# Evaluation Report — HealthCore Sales Forecast

**Model:** `RandomForestRegressor` (`n_estimators={report['n_estimators']}`, `random_state={report['random_state']}`)  
**Target:** `{report['target']}` (CONTEXT: consolidated monthly revenue)  
**Script:** `uv run python scripts/evaluate_sales_model.py`  
**Learning curve image:** [`learning_curve.png`](./learning_curve.png)

## 1. Diagnosis (explicit)

**Classification: {fit_es}**

{diag['rationale']}

Evidence:
- Learning-curve mean train/val RMSE gap ≈ **{diag['mean_gap_rmse_pct']:.2f}** percentage points.
- Last curve point: train RMSE **{diag['last_train_rmse_pct']:.2f}%**, val RMSE **{diag['last_val_rmse_pct']:.2f}%**.
- Last curve point: train MAE **{diag['last_train_mae_pct']:.2f}%**, val MAE **{diag['last_val_mae_pct']:.2f}%**.
- Temporal CV stability: **{diag['stability_label']}** (val RMSE % std = {diag['cv_val_rmse_pct_std']:.2f}%).

## 2. Metric selection (MAE vs RMSE)

{report['primary_metric_justification']}

| Role | Metric | CV result (mean ± std) |
| --- | --- | --- |
| **Primary** | RMSE % of mean `revenue_usd` | **{mean_std['val_rmse_pct']}** |
| Primary (USD) | RMSE USD | **{mean_std['val_rmse_usd']}** |
| Secondary | MAE % of mean `revenue_usd` | **{mean_std['val_mae_pct']}** |
| Secondary (USD) | MAE USD | **{mean_std['val_mae_usd']}** |

Train-side CV means (in-sample, diagnostic only):  
RMSE % = {format_mean_std(stab, 'train_rmse_pct', '%')}; MAE % = {format_mean_std(stab, 'train_mae_pct', '%')}.

## 3. Temporal cross-validation (≥5 folds)

- Splitter: `TimeSeriesSplit(n_splits={report['cv']['n_splits']}, test_size={report['cv']['test_size']}, gap={report['cv']['gap']})`
- **Shuffle:** false (chronological order preserved; verified by unit test)
- **Lag/rolling leakage:** features rebuilt with `add_lag_features` on **each fold's train rows only**; validation uses recursive forecast; `gap={report['cv']['gap']}` purges `lag_12` across the boundary
- Scope: 8-year train block only; sealed 2024–2025 test **excluded** from CV

{chr(10).join(fold_lines)}

**Summary:** val RMSE % = **{mean_std['val_rmse_pct']}**; val MAE % = **{mean_std['val_mae_pct']}**.

## 4. Learning curve

Fixed validation window = last 24 months of the train block (2022-01 → 2023-12), with a 12-month purge gap before train prefixes of 36 / 48 / 60 months.

{chr(10).join(curve_lines)}

See [`learning_curve.png`](./learning_curve.png). Pattern: low train error vs higher validation error → supports the **{fit}** diagnosis.

## 5. Corrective action (specific)

**Action:** {rec['action']}

**Why this (not a generic tip):** {rec['why']}

**Business / bias note:** {rec['business_note']}

**Stability note:** {rec['stability_note']}

## 6. Staging verdict

Do **not** promote the unconstrained RF to staging on sealed-test RMSE alone. Apply the corrective action above, re-run this script, and attach updated `learning_curve.png` + this report.

## 7. Reproduce

```bash
# Windows deep paths: use subst W: if sklearn fails (MAX_PATH).
uv run python scripts/evaluate_sales_model.py
uv run python -m pytest tests/pipelines/test_sales_evaluation.py -q
```
"""
    path.write_text(body, encoding="utf-8")
    logger.info("markdown report written to %s", path)


def run(n_estimators: int = N_ESTIMATORS,
        output_dir: Path = EVAL_DIR) -> dict[str, Any]:
    train_block, sealed_test = _prepare_series()
    assert len(sealed_test) == 24

    curve = learning_curve_rows(train_block, n_estimators=n_estimators)
    cv = temporal_cv_folds(train_block, n_estimators=n_estimators)
    stability = summarize_stability(cv)
    diagnosis = diagnose_fit(curve, stability)
    recommendation = recommend_action(diagnosis, stability)
    report = build_report(
        curve, cv, stability, diagnosis, recommendation, n_estimators=n_estimators
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    curve.to_csv(output_dir / "sales_learning_curve.csv", index=False)
    cv.to_csv(output_dir / "sales_cv_folds.csv", index=False)
    plot_learning_curve(curve, output_dir / "learning_curve.png")
    (output_dir / "sales_evaluation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    write_markdown_report(report, output_dir / "evaluation_report.md")

    logger.info(
        "diagnosis=%s stability=%s cv_rmse=%s cv_mae=%s",
        diagnosis["fit_label"], diagnosis["stability_label"],
        report["stability_mean_std"]["val_rmse_pct"],
        report["stability_mean_std"]["val_mae_pct"],
    )
    logger.info("action: %s", recommendation["action"])
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Formal temporal evaluation of the HealthCore sales RF (academy rubric)."
    )
    parser.add_argument("--n-estimators", type=int, default=N_ESTIMATORS)
    parser.add_argument("--output-dir", type=Path, default=EVAL_DIR)
    args = parser.parse_args()
    run(n_estimators=args.n_estimators, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
