"""Readability metrics to anticipate LLM processing cost (not literary grade)."""

from __future__ import annotations

from typing import Any


def compute_readability_metrics(markdown: str) -> dict[str, Any]:
    """Return Flesch-Kincaid / Gunning Fog style metrics for the Markdown body."""
    text = (markdown or "").strip()
    if not text:
        return {
            "flesch_kincaid_grade": None,
            "gunning_fog": None,
            "flesch_reading_ease": None,
            "word_count": 0,
        }

    try:
        from readability import Readability

        r = Readability(text)
        fk = r.flesch_kincaid()
        fog = r.gunning_fog()
        ease = r.flesch()
        return {
            "flesch_kincaid_grade": float(fk.score),
            "gunning_fog": float(fog.score),
            "flesch_reading_ease": float(ease.score),
            "word_count": len(text.split()),
        }
    except Exception:  # noqa: BLE001 - short docs / analyzer edge cases
        words = text.split()
        return {
            "flesch_kincaid_grade": None,
            "gunning_fog": None,
            "flesch_reading_ease": None,
            "word_count": len(words),
            "note": "readability_unavailable",
        }
