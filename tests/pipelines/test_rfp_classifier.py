"""Unit tests for the RFP intake classifier agent."""

from __future__ import annotations

from pathlib import Path

from data.pipelines.rfp_intake.classifier import classify_rfp, classify_rfp_heuristic

FIXTURES = Path(__file__).parent / "fixtures" / "rfp_intake"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_classifier_accepts_formal_meridian_rfp() -> None:
    result = classify_rfp_heuristic(_load("formal_meridian.md"))
    assert result.is_rfp is True
    assert result.confidence >= 0.5


def test_classifier_accepts_informal_thames_partnership() -> None:
    result = classify_rfp_heuristic(_load("informal_thames.md"))
    assert result.is_rfp is True


def test_classifier_rejects_ehr_vendor_pitch() -> None:
    result = classify_rfp_heuristic(_load("invalid_ehr_vendor.md"))
    assert result.is_rfp is False
    assert "vendor" in result.reason.lower() or "pitch" in result.reason.lower()


def test_classify_rfp_falls_back_without_llm(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    result = classify_rfp(_load("formal_meridian.md"))
    assert result.is_rfp is True
