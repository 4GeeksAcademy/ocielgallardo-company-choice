"""Operational telemetry metrics — SQL load, Pandas transform, JSON-serializable out.

Pure functions: same (conn, start_date, end_date) → same list[dict].
Window is applied only in SQL (inclusive start, exclusive end). No HTTP/cache here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.engine import Connection, Engine

ERROR_EVENT_TYPES = frozenset(
    {
        "frontend_error_captured",
        "http_request_failed",
        "login_failed",
        "session_expired",
    }
)

_WINDOW_PARAMS = "timestamp >= %(start)s AND timestamp < %(end)s"


def _read_events(
    conn: Connection | Engine,
    sql: str,
    params: dict[str, Any],
) -> pd.DataFrame:
    """Load a filtered event slice. Caller must include a timestamp window in SQL."""
    return pd.read_sql(sql, conn, params=params)


def _with_utc_date(df: pd.DataFrame) -> pd.DataFrame:
    """Convert timestamps to UTC datetime before any temporal groupby."""
    if df.empty:
        return df
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    out["date"] = out["timestamp"].dt.date
    return out


def _date_str(series: pd.Series) -> pd.Series:
    return series.astype(str)


def events_per_day(
    conn: Connection | Engine,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """Daily event volume — how noisy is the system each day?"""
    sql = f"""
        SELECT timestamp, event_type
        FROM telemetry_events
        WHERE {_WINDOW_PARAMS}
    """
    df = _read_events(conn, sql, {"start": start_date, "end": end_date})
    if df.empty:
        return []

    df = _with_utc_date(df)
    grouped = (
        df.groupby("date", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    grouped["date"] = _date_str(grouped["date"])
    return grouped.to_dict(orient="records")


def error_rate_by_type(
    conn: Connection | Engine,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """Per-day error share by event_type vs all events that day.

    Loads every event_type in the window so the denominator exists.
    """
    sql = f"""
        SELECT timestamp, event_type
        FROM telemetry_events
        WHERE {_WINDOW_PARAMS}
    """
    df = _read_events(conn, sql, {"start": start_date, "end": end_date})
    if df.empty:
        return []

    df = _with_utc_date(df)
    df["is_error"] = df["event_type"].isin(ERROR_EVENT_TYPES)

    daily_total = (
        df.groupby("date", as_index=False)
        .size()
        .rename(columns={"size": "total_count"})
    )

    errors = df.loc[df["is_error"]]
    if errors.empty:
        return []

    error_counts = (
        errors.groupby(["date", "event_type"], as_index=False)
        .size()
        .rename(columns={"size": "error_count"})
    )
    merged = error_counts.merge(daily_total, on="date", how="left")
    merged["rate"] = (merged["error_count"] / merged["total_count"]).round(6)
    merged["date"] = _date_str(merged["date"])
    return merged[
        ["date", "event_type", "error_count", "total_count", "rate"]
    ].to_dict(orient="records")


def avg_latency_by_path(
    conn: Connection | Engine,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """Mean API latency (ms) per day and path from api_latency_recorded tags."""
    sql = f"""
        SELECT timestamp, tags
        FROM telemetry_events
        WHERE {_WINDOW_PARAMS}
          AND event_type = %(event_type)s
    """
    df = _read_events(
        conn,
        sql,
        {
            "start": start_date,
            "end": end_date,
            "event_type": "api_latency_recorded",
        },
    )
    if df.empty:
        return []

    df = _with_utc_date(df)
    tags = pd.json_normalize(df["tags"])
    df = df.join(tags[["path", "duration_ms"]], how="left")
    df = df.dropna(subset=["path", "duration_ms"])
    if df.empty:
        return []

    df["duration_ms"] = pd.to_numeric(df["duration_ms"], errors="coerce")
    df = df.dropna(subset=["duration_ms"])
    if df.empty:
        return []

    grouped = (
        df.groupby(["date", "path"], as_index=False)
        .agg(avg_duration_ms=("duration_ms", "mean"), sample_count=("duration_ms", "size"))
    )
    grouped["avg_duration_ms"] = grouped["avg_duration_ms"].round(2)
    grouped["date"] = _date_str(grouped["date"])
    return grouped.to_dict(orient="records")


def auth_failure_rate(
    conn: Connection | Engine,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    """Daily login failure rate: failed / (failed + succeeded).

    Loads both auth event types in one SQL query so the denominator exists.
    """
    sql = f"""
        SELECT timestamp, event_type
        FROM telemetry_events
        WHERE {_WINDOW_PARAMS}
          AND event_type IN ('login_failed', 'login_succeeded')
    """
    df = _read_events(conn, sql, {"start": start_date, "end": end_date})
    if df.empty:
        return []

    df = _with_utc_date(df)
    counts = (
        df.groupby(["date", "event_type"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    pivot = (
        counts.pivot(index="date", columns="event_type", values="count")
        .fillna(0)
        .reset_index()
    )
    if "login_failed" not in pivot.columns:
        pivot["login_failed"] = 0
    if "login_succeeded" not in pivot.columns:
        pivot["login_succeeded"] = 0

    pivot["failed"] = pivot["login_failed"].astype(int)
    pivot["succeeded"] = pivot["login_succeeded"].astype(int)
    pivot["total_attempts"] = pivot["failed"] + pivot["succeeded"]
    pivot["rate"] = (pivot["failed"] / pivot["total_attempts"]).round(6)
    pivot["date"] = _date_str(pivot["date"])
    return pivot[
        ["date", "failed", "succeeded", "total_attempts", "rate"]
    ].to_dict(orient="records")


def build_report(
    conn: Connection | Engine,
    start_date: datetime,
    end_date: datetime,
) -> dict[str, Any]:
    """Assemble all operational metrics for a resolved period."""
    return {
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
        "metrics": {
            "events_per_day": events_per_day(conn, start_date, end_date),
            "error_rate_by_type": error_rate_by_type(conn, start_date, end_date),
            "avg_latency_by_path": avg_latency_by_path(conn, start_date, end_date),
            "auth_failure_rate": auth_failure_rate(conn, start_date, end_date),
        },
    }
