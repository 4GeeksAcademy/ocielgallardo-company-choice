"""EN -> ES aware product matching for inventory stock questions."""

from types import SimpleNamespace

import pytest

from data.pipelines.inventory_search import filter_products, fold

CATALOGUE = [
    SimpleNamespace(name="Guantes de nitrilo (caja de 100)"),
    SimpleNamespace(name="Mascarilla quirúrgica (pack de 50)"),
    SimpleNamespace(name="Apósito adhesivo para heridas"),
    SimpleNamespace(name="Test rápido de estreptococo"),
    SimpleNamespace(name="Tiras reactivas glucemia (50)"),
    SimpleNamespace(name="Solución salina 0,9% 500ml"),
]


def _names(query: str) -> list[str]:
    return [item.name for item in filter_products(CATALOGUE, query)]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("surgical gloves", "Guantes de nitrilo (caja de 100)"),
        ("gloves", "Guantes de nitrilo (caja de 100)"),
        ("nitrile gloves", "Guantes de nitrilo (caja de 100)"),
        ("nitrilo guantes", "Guantes de nitrilo (caja de 100)"),
        ("glovse", "Guantes de nitrilo (caja de 100)"),
        ("surgical masks", "Mascarilla quirúrgica (pack de 50)"),
        ("mascarilla quirurgica", "Mascarilla quirúrgica (pack de 50)"),
        ("bandages", "Apósito adhesivo para heridas"),
        ("strep test", "Test rápido de estreptococo"),
        ("blood glucose test strips", "Tiras reactivas glucemia (50)"),
        ("saline", "Solución salina 0,9% 500ml"),
    ],
)
def test_english_and_spanish_queries_find_the_product(query, expected) -> None:
    assert _names(query) == [expected]


@pytest.mark.parametrize(
    "query", ["unicorn", "dental implants", "covid test", "guantes latex", "masks gloves", "gl"]
)
def test_unknown_terms_never_produce_absurd_matches(query) -> None:
    assert _names(query) == []


def test_fold_strips_accents_and_case() -> None:
    assert fold("Quirúrgica SOLUCIÓN") == "quirurgica solucion"
