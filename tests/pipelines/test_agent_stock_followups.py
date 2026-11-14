"""Stock questions: face masks / syringes, Spanish intent, retry after "not found"."""

from __future__ import annotations

import pytest

from data.pipelines import agent_graph, mcp_client
from data.pipelines import rag as rag_pipeline
from data.pipelines.agent_graph import (
    classify_route,
    extract_inventory_name_query,
    resolve_follow_up,
    run_agent,
)
from data.pipelines.agent_tools import (
    INCIDENT_NOT_FOUND_MESSAGE,
    INVENTORY_NOT_FOUND_MESSAGE,
    InventoryRecord,
    InventoryToolOutput,
)
from data.pipelines.inventory_search import filter_products

CATALOGUE = [
    InventoryRecord(id=1, name="Guantes de nitrilo (caja de 100)", sku="HCR-PPE-001",
                    category="ppe", unit="box", country="US", current_stock=1289),
    InventoryRecord(id=2, name="Mascarilla quirúrgica (pack de 50)", sku="HCR-PPE-002",
                    category="ppe", unit="pack", country="UK", current_stock=640),
    InventoryRecord(id=3, name="Solución salina 0,9% 500ml", sku="HCR-MED-001",
                    category="medications", unit="vial", country="US", current_stock=80),
]


@pytest.fixture(autouse=True)
def _mcp_on(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:8100/mcp")
    agent_graph._PENDING_CLARIFICATIONS.clear()
    yield
    agent_graph._PENDING_CLARIFICATIONS.clear()


@pytest.fixture
def inventory(monkeypatch):
    """Fake MCP inventory tool that runs the real product matcher."""
    seen: list = []

    def _lookup(payload, **kw):
        seen.append(payload)
        products = filter_products(CATALOGUE, payload.name_query or "")
        if not products:
            return InventoryToolOutput(
                ok=False, error="not_found", message=INVENTORY_NOT_FOUND_MESSAGE
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


# --- Fix 1: face masks / syringes reach the right product (or honest not found) ---


def test_face_masks_question_answers_with_the_surgical_mask(inventory, no_rag) -> None:
    result = run_agent("How many face masks do we have in stock?", session_id="s1")
    assert inventory[-1].name_query == "face masks"
    assert "Mascarilla quirúrgica" in result["answer"]
    assert no_rag == []


def test_syringes_are_not_in_the_catalogue_and_fail_honestly(inventory, no_rag) -> None:
    result = run_agent("How much stock of syringes?", session_id="s1")
    assert inventory[-1].name_query == "syringes"
    assert result["answer"].startswith(INVENTORY_NOT_FOUND_MESSAGE)


# --- Fix 2: the reply after "could not find that product" retries the stock tool ---


def test_bare_product_after_not_found_retries_the_stock_tool(inventory, no_rag) -> None:
    first = run_agent("How much stock of unicorn dust?", session_id="s2")
    assert first["answer"].startswith(INVENTORY_NOT_FOUND_MESSAGE)

    second = run_agent("face masks", session_id="s2")

    assert inventory[-1].name_query == "face masks"
    assert "Mascarilla quirúrgica" in second["answer"]
    assert no_rag == []  # never sent to the knowledge base


def test_bare_product_still_missing_stays_an_honest_not_found(inventory, no_rag) -> None:
    run_agent("How much stock of syringes?", session_id="s3")
    second = run_agent("syringes", session_id="s3")
    assert len(inventory) == 2
    assert second["answer"].startswith(INVENTORY_NOT_FOUND_MESSAGE)
    assert no_rag == []


def test_not_found_follow_up_rewrites_and_skips_acknowledgements() -> None:
    agent_graph._remember_clarification("a", INVENTORY_NOT_FOUND_MESSAGE)
    assert resolve_follow_up("a", "syringes") == "What is the current stock of syringes?"

    agent_graph._remember_clarification("a", INVENTORY_NOT_FOUND_MESSAGE)
    assert resolve_follow_up("a", "thanks") == "thanks"

    agent_graph._remember_clarification("a", INVENTORY_NOT_FOUND_MESSAGE)
    assert resolve_follow_up("a", "What is the cancellation fee?") == (
        "What is the cancellation fee?"
    )


def test_ticket_not_found_follow_up_reads_a_bare_number() -> None:
    agent_graph._remember_clarification("a", INCIDENT_NOT_FOUND_MESSAGE)
    assert resolve_follow_up("a", "8") == "What is the status of ticket 8?"


# --- Fix 4: Spanish stock intent ---


@pytest.mark.parametrize(
    "question",
    [
        "¿Cuántos guantes de nitrilo quedan?",
        "¿Cuántas mascarillas hay?",
        "¿Hay jeringas?",
        "Cuantos guantes nos quedan",
        "¿Qué stock hay de solución salina?",
        "Inventario de guantes de nitrilo",
        "How many gloves are left?",
    ],
)
def test_stock_questions_without_the_word_stock_route_to_inventory(question) -> None:
    assert classify_route(question) == "inventory"


@pytest.mark.parametrize(
    "question",
    [
        "¿Cuántos días hay para cancelar una cita?",
        "¿Cuántas clínicas hay en Texas?",
        "How many patients do we see per day?",
        "What documents does a new patient need to bring?",
    ],
)
def test_quantity_words_alone_do_not_route_to_inventory(question) -> None:
    assert classify_route(question) == "rag"


def test_spanish_nitrile_gloves_question_answers_with_stock(inventory, no_rag) -> None:
    result = run_agent("¿Cuántos guantes de nitrilo quedan?", session_id="es")
    assert extract_inventory_name_query("¿Cuántos guantes de nitrilo quedan?") == (
        "guantes nitrilo"
    )
    assert inventory[-1].name_query == "guantes nitrilo"
    assert "1,289" in result["answer"]
    assert "Guantes de nitrilo" in result["answer"]
    assert no_rag == []
