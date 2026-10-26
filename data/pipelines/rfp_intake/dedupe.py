"""Normalize and deduplicate open-question strings across workers/synthesizer."""

from __future__ import annotations

import re


def _normalize_question(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    cleaned = cleaned.rstrip("?.! ")
    return cleaned


def dedupe_questions(questions: list[str] | None) -> list[str]:
    """Keep first occurrence; drop near-duplicates (same normalized text)."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in questions or []:
        q = str(raw).strip()
        if not q:
            continue
        key = _normalize_question(q)
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out
