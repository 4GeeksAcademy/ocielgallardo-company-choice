"""Inventory replies must survive the output guard; clinical advice must not."""

from __future__ import annotations

import pytest

from data.pipelines import agent_content_guard as guard
from data.pipelines import agent_graph, mcp_client
from data.pipelines import rag as rag_pipeline
from data.pipelines.agent_graph import (
    is_inventory_topic_clarification,
    resolve_inventory_topic_clarification,
    run_agent,
)
from data.pipelines.agent_tools import InventoryRecord, InventoryToolOutput
from data.pipelines.inventory_search import filter_products
from services.app.core.inventory_seed import MEDICAL_SUPPLIES_SEED

SEED_CATALOGUE = [
    InventoryRecord(
        id=index + 1,
        name=row["name"],
        sku=row["sku"],
        category=row["category"],
        unit=row["unit"],
        country=row["country"],
        current_stock=1100 - index * 10,
    )
    for index, row in enumerate(MEDICAL_SUPPLIES_SEED)
]


@pytest.fixture(autouse=True)
def _mcp_on(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:8100/mcp")
    agent_graph._PENDING_CLARIFICATIONS.clear()
    agent_graph._LAST_INVENTORY_MISS.clear()
    agent_graph._LAST_INVENTORY_QUESTION.clear()
    guard.reset_activations()
    yield
    agent_graph._PENDING_CLARIFICATIONS.clear()
    agent_graph._LAST_INVENTORY_MISS.clear()
    agent_graph._LAST_INVENTORY_QUESTION.clear()


@pytest.fixture
def inventory(monkeypatch):
    seen: list = []

    def _lookup(payload, **kw):
        seen.append(payload)
        if payload.list_all:
            return InventoryToolOutput(ok=True, products=[], catalogue=list(SEED_CATALOGUE))
        products = filter_products(SEED_CATALOGUE, payload.name_query or "")
        if payload.sku:
            sku = payload.sku.strip().upper()
            products = [item for item in SEED_CATALOGUE if item.sku.upper() == sku]
        if not products:
            return InventoryToolOutput(
                ok=True,
                products=[],
                catalogue=list(SEED_CATALOGUE),
                queried_name=payload.name_query or payload.sku,
            )
        return InventoryToolOutput(ok=True, products=products)

    monkeypatch.setattr(mcp_client, "lookup_inventory_via_mcp", _lookup)
    return seen


@pytest.fixture
def no_rag(monkeypatch):
    calls: list[str] = []

    def _retrieve(question, **kw):
        calls.append(question)
        return []

    monkeypatch.setattr(rag_pipeline, "retrieve", _retrieve)
    monkeypatch.setattr(
        rag_pipeline,
        "generate_answer_with_proposal",
        lambda q, c, *, memory=None: ("KB answer.", None),
    )
    return calls


def _assert_not_blocked(result: dict) -> None:
    assert result["answer"] != guard.OUTPUT_FALLBACK_EN
    assert "I can't share that response" not in result["answer"]
    verdict = guard.validate_output(result["answer"])
    assert verdict.allowed is True
    assert "clinical_content" not in verdict.reasons


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("How much stock of syringes?", "We don't stock syringes."),
        ("¿Cuántos guantes de nitrilo quedan?", "Guantes de nitrilo"),
        ("How many face masks do we have in stock?", "Mascarilla quirúrgica"),
    ],
)
def test_full_inventory_replies_pass_the_content_guard(
    inventory, no_rag, question, expected
) -> None:
    result = run_agent(question, session_id="guard")
    _assert_not_blocked(result)
    assert expected in result["answer"]
    assert "SKU " in result["answer"]
    assert no_rag == []
    summary = guard.get_activation_summary()
    assert "output_rejected" not in summary


def test_clinical_advice_is_still_blocked_by_the_output_guard(monkeypatch) -> None:
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:8100/mcp")
    monkeypatch.setattr(rag_pipeline, "retrieve", lambda q, **kw: [{"text": "policy"}])
    monkeypatch.setattr(
        rag_pipeline,
        "generate_answer_with_proposal",
        lambda q, c, *, memory=None: (
            "Based on those symptoms, the diagnosis is streptococcal pharyngitis. "
            "I recommend starting antibiotics today.",
            None,
        ),
    )

    result = run_agent("What is the cancellation fee if I miss an appointment?", session_id="advice")

    assert result["answer"] == guard.OUTPUT_FALLBACK_EN
    assert "diagnosis" not in result["answer"]
    assert "symptoms" not in result["answer"]
    assert "antibiotics" not in result["answer"]


@pytest.mark.parametrize(
    "message",
    [
        "This question is about inventory.",
        "This quest is about inventory.",
        "it's about inventory",
        "Es una pregunta de inventario.",
    ],
)
def test_inventory_topic_clarification_is_detected(message) -> None:
    assert is_inventory_topic_clarification(message)
    assert not is_inventory_topic_clarification("What is the inventory policy?")


def test_inventory_clarification_retries_the_last_stock_question(inventory, no_rag) -> None:
    first = run_agent("How much stock of syringes?", session_id="retry")
    _assert_not_blocked(first)
    generated_before = list(no_rag)

    second = run_agent("This question is about inventory.", session_id="retry")

    _assert_not_blocked(second)
    assert second["answer"].startswith("We don't stock syringes.")
    assert "Test rápido de estreptococo (SKU HCR-DIAG-001)" in second["answer"]
    assert no_rag == generated_before


def test_inventory_clarification_retries_after_a_blocked_stock_reply(
    inventory, no_rag, monkeypatch
) -> None:
    calls = {"n": 0}
    real = guard.validate_output

    def _once_blocked(answer, *, skip_reasons=()):
        calls["n"] += 1
        if calls["n"] == 1:
            return guard.OutputVerdict(
                allowed=False,
                reasons=["clinical_content"],
                safe_answer=guard.OUTPUT_FALLBACK_EN,
                failure_type=guard.FAILURE_CONTENT,
            )
        return real(answer, skip_reasons=skip_reasons)

    monkeypatch.setattr(guard, "validate_output", _once_blocked)

    first = run_agent("How much stock of syringes?", session_id="blocked")
    assert first["answer"] == guard.OUTPUT_FALLBACK_EN

    second = run_agent("This quest is about inventory.", session_id="blocked")

    assert second["answer"].startswith("We don't stock syringes.")
    assert "I can't share that response" not in second["answer"]
    assert no_rag == []


def test_clarification_without_a_prior_stock_question_lists_the_catalogue(
    inventory, no_rag
) -> None:
    result = run_agent("This question is about inventory.", session_id="fresh")
    _assert_not_blocked(result)
    assert result["answer"].startswith("Products currently in inventory:")
    assert "SKU HCR-PPE-001" in result["answer"]
    assert no_rag == []


def test_resolve_inventory_topic_clarification_replays_the_last_question() -> None:
    agent_graph._remember_inventory_question("s", "How much stock of syringes?")
    assert resolve_inventory_topic_clarification(
        "s", "This question is about inventory."
    ) == "How much stock of syringes?"
    assert resolve_inventory_topic_clarification("s", "How many gloves?") == "How many gloves?"
