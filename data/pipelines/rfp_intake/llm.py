"""Optional OpenAI-compatible LLM helper for RFP intake agents."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def llm_available() -> bool:
    return bool(os.getenv("LLM_API_KEY", "").strip() and os.getenv("LLM_MODEL", "").strip())


def chat_json(system: str, user: str, *, temperature: float = 0.1) -> dict[str, Any] | None:
    """Ask the configured LLM for a JSON object. Returns None if unavailable/fails."""
    if not llm_available():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1"),
        )
        completion = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", ""),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw = (completion.choices[0].message.content or "").strip()
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        logger.exception("RFP intake LLM call failed; falling back to heuristics")
        return None


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object from model text."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
