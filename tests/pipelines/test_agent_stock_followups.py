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
    format_not_stocked_answer,
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
    agent_graph._LAST_INVENTORY_MISS.clear()
    yield
    agent_graph._PENDING_CLARIFICATIONS.clear()
    agent_graph._LAST_INVENTORY_MISS.clear()


@pytest.fixture
def inventory(monkeypatch):
    """Fake MCP inventory tool that runs the real product matcher."""
    seen: list = []

    def _lookup(payload, **kw):
        seen.append(payload)
        if payload.list_all:
            return InventoryToolOutput(ok=True, products=[], catalogue=list(CATALOGUE))
        products = filter_products(CATALOGUE, payload.name_query or "")
        if payload.sku:
            sku = payload.sku.strip().upper()
            products = [item for item in CATALOGUE if item.sku.upper() == sku]
        if not products:
            return InventoryToolOutput(
                ok=True,
                products=[],
                catalogue=list(CATALOGUE),
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


# --- Fix 1: face masks / syringes reach the right product (or honest not found) ---


def test_face_masks_question_answers_with_the_surgical_mask(inventory, no_rag) -> None:
    result = run_agent("How many face masks do we have in stock?", session_id="s1")
    assert inventory[-1].name_query == "face masks"
    assert "Mascarilla quirúrgica" in result["answer"]
    assert no_rag == []


def test_syringes_are_not_in_the_catalogue_and_list_what_is_stocked(
    inventory, no_rag
) -> None:
    result = run_agent("How much stock of syringes?", session_id="s1")
    assert inventory[-1].name_query == "syringes"
    assert result["answer"] == format_not_stocked_answer("syringes", CATALOGUE)
    assert result["answer"].startswith("We don't stock syringes.")
    assert "SKU HCR-PPE-001" in result["answer"]
    assert "SKU HCR-PPE-002" in result["answer"]
    assert "I could not find that product" not in result["answer"]
    assert "Could not complete this" not in result["answer"]
    assert no_rag == []


# --- Fix 2: the reply after "could not find that product" retries the stock tool ---


def test_bare_product_after_not_found_retries_the_stock_tool(inventory, no_rag) -> None:
    first = run_agent("How much stock of unicorn dust?", session_id="s2")
    assert first["answer"].startswith("We don't stock unicorn dust.")

    second = run_agent("face masks", session_id="s2")

    assert inventory[-1].name_query == "face masks"
    assert "Mascarilla quirúrgica" in second["answer"]
    assert no_rag == []  # never sent to the knowledge base


def test_bare_product_still_missing_stays_a_normal_not_stocked_answer(
    inventory, no_rag
) -> None:
    run_agent("How much stock of syringes?", session_id="s3")
    second = run_agent("syringes", session_id="s3")
    assert len(inventory) == 2
    assert second["answer"] == format_not_stocked_answer("syringes", CATALOGUE)
    assert "I could not find that product" not in second["answer"]
    assert no_rag == []


def test_similar_product_follow_up_lists_the_catalogue(inventory, no_rag) -> None:
    first = run_agent("How much stock of syringes?", session_id="s4")
    assert first["answer"].startswith("We don't stock syringes.")

    second = run_agent("Is there one product in stock like that?", session_id="s4")

    assert inventory[-1].list_all is True
    assert second["answer"].startswith("We don't stock syringes.")
    assert "Products currently in inventory:" in second["answer"]
    assert "SKU HCR-PPE-001" in second["answer"]
    assert "I could not find that product" not in second["answer"]
    assert no_rag == []


def test_not_found_follow_up_rewrites_and_skips_acknowledgements() -> None:
    not_stocked = format_not_stocked_answer("unicorn dust", CATALOGUE)
    agent_graph._remember_clarification("a", not_stocked)
    assert resolve_follow_up("a", "syringes") == "What is the current stock of syringes?"

    agent_graph._remember_clarification("a", not_stocked)
    assert resolve_follow_up("a", "thanks") == "thanks"

    agent_graph._remember_clarification("a", not_stocked)
    assert resolve_follow_up("a", "What is the cancellation fee?") == (
        "What is the cancellation fee?"
    )

    agent_graph._remember_clarification("a", not_stocked)
    assert resolve_follow_up("a", "Is there one product in stock like that?") == (
        "What products are currently in inventory?"
    )

    # Legacy wording still rewrites a bare product name.
    agent_graph._remember_clarification("a", INVENTORY_NOT_FOUND_MESSAGE)
    assert resolve_follow_up("a", "syringes") == "What is the current stock of syringes?"


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
