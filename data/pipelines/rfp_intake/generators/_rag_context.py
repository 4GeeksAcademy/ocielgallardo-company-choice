"""Optional RAG grounding for drafting generators (soft-fail + hard timeout)."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

logger = logging.getLogger(__name__)

_RAG_TIMEOUT_SEC = float(os.getenv("RFP_DRAFT_RAG_TIMEOUT_SEC", "4"))
_RAG_ENABLED = os.getenv("RFP_DRAFT_USE_RAG", "0").strip().lower() in {
    "1",
    "true",
    "yes",
}


def fetch_grounding_snippets(query: str, *, k: int = 3) -> list[str]:
    """Return short policy snippets; empty list on disable/timeout/failure."""
    if not _RAG_ENABLED:
        return []

    def _run() -> list[str]:
        from data.pipelines.rag import retrieve

        hits = retrieve(query, k=k)
        snippets: list[str] = []
        for hit in hits:
            text = (hit.get("text") or "").strip()
            if text:
                snippets.append(text[:800])
        return snippets

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run)
            return fut.result(timeout=_RAG_TIMEOUT_SEC)
    except FuturesTimeout:
        logger.warning("RFP generator RAG timed out after %ss", _RAG_TIMEOUT_SEC)
        return []
    except Exception:  # noqa: BLE001
        logger.info("RFP generator RAG unavailable; continuing without grounding")
        return []


def format_grounding(snippets: list[str]) -> str:
    if not snippets:
        return ""
    bullets = "\n".join(f"- {s}" for s in snippets[:3])
    return (
        "\n\n### Internal policy grounding (do not invent beyond this)\n"
        f"{bullets}\n"
    )


def aspects_block(key_aspects: list[Any]) -> str:
    if not key_aspects:
        return "(No intake key aspects recorded.)"
    return "\n".join(f"- {a}" for a in key_aspects)
