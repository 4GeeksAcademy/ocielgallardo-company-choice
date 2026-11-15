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


@pytest.mark.parametrize(
    "query",
    ["face masks", "facial masks", "face mask", "mascarillas", "protective face masks"],
)
def test_face_masks_find_the_surgical_mask(query) -> None:
    assert _names(query) == ["Mascarilla quirúrgica (pack de 50)"]


@pytest.mark.parametrize("query", ["syringes", "syringe", "needles", "gauze"])
def test_known_supplies_missing_from_the_catalogue_are_not_found(query) -> None:
    # No syringes / needles / gauze in the catalogue: honest "not found",
    # never a different product.
    assert _names(query) == []


def test_syringes_match_a_spanish_named_product_once_it_exists() -> None:
    catalogue = [*CATALOGUE, SimpleNamespace(name="Jeringas 5ml (caja de 100)")]
    names = [item.name for item in filter_products(catalogue, "syringes")]
    assert names == ["Jeringas 5ml (caja de 100)"]


def test_face_alone_does_not_match_anything() -> None:
    # A soft term alone must still match something in the name.
    assert _names("face") == []
