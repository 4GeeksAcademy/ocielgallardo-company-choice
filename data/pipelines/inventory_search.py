"""Product-name matching for inventory stock questions (EN -> ES aware).

Responsibility: decide which inventory products a free-text product query
refers to. The catalogue is seeded with Spanish product names ("Guantes de
nitrilo (caja de 100)") while staff usually ask in English ("surgical
gloves"), so plain substring matching misses obvious products.

Rules (deterministic, no LLM, no network):

- Text is lower-cased and accent-folded on both sides ("quirúrgica" ==
  "quirurgica").
- Each query term is expanded with a small English -> Spanish synonym map
  (``gloves`` -> ``guante``). Unknown terms are matched as-is, so Spanish
  queries ("nitrilo guantes") keep working.
- *Core* terms (the product noun, e.g. ``gloves``) must all match. *Soft*
  terms (``surgical``, ``medical``, ``disposable``, ``box`` …) only rank the
  results: "surgical gloves" still finds the nitrile gloves because the
  catalogue has no separate surgical gloves.
- A query made only of soft terms requires at least one of them to match.
- Typos are tolerated with a strict fuzzy ratio on words of 5+ characters
  ("glovse" -> gloves), never on short words, to avoid absurd matches.
- A term that matches nothing (``unicorn``, ``implant``) makes the whole
  query fail: an honest "not found" beats a wrong product.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Protocol, TypeVar

# English (and common variants) -> Spanish stems found in product names.
EN_ES_SYNONYMS: dict[str, tuple[str, ...]] = {
    "glove": ("guante",),
    "gloves": ("guante",),
    "nitrile": ("nitrilo",),
    "mask": ("mascarilla",),
    "masks": ("mascarilla",),
    "facemask": ("mascarilla",),
    "facemasks": ("mascarilla",),
    "surgical": ("quirurgic",),
    "bandage": ("aposito",),
    "bandages": ("aposito",),
    "dressing": ("aposito",),
    "dressings": ("aposito",),
    "plaster": ("aposito",),
    "plasters": ("aposito",),
    "band-aid": ("aposito",),
    "band-aids": ("aposito",),
    "bandaid": ("aposito",),
    "bandaids": ("aposito",),
    "adhesive": ("adhesiv",),
    "wound": ("herida",),
    "wounds": ("herida",),
    "strep": ("estreptococo",),
    "streptococcus": ("estreptococo",),
    "rapid": ("rapido",),
    "test": ("test",),
    "tests": ("test",),
    "glucose": ("glucemia",),
    "glucometer": ("glucemia",),
    "sugar": ("glucemia",),
    "strip": ("tira",),
    "strips": ("tira",),
    "reagent": ("reactiva",),
    "saline": ("salina",),
    "solution": ("solucion",),
    "box": ("caja",),
    "boxes": ("caja",),
    "pack": ("pack",),
    "packs": ("pack",),
}

# Descriptive words that rank results but are never required on their own
# when a core term is present.
SOFT_TERMS: frozenset[str] = frozenset(
    {
        "surgical",
        "medical",
        "disposable",
        "sterile",
        "box",
        "boxes",
        "pack",
        "packs",
        "kit",
        "kits",
        "rapid",
        "adhesive",
        "reagent",
        "blood",
        "test",
        "tests",
        "quirurgico",
        "quirurgica",
        "medico",
        "medica",
        "desechable",
        "desechables",
        "esteril",
        "caja",
        "cajas",
    }
)

_FUZZY_MIN_LEN = 5
_FUZZY_CUTOFF = 0.85
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def fold(text: str) -> str:
    """Lower-case and strip accents ("Quirúrgica" -> "quirurgica")."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def query_terms(name_query: str) -> list[str]:
    """Split a product query into folded words (punctuation dropped).

    Words shorter than 3 characters ("gl", "de") are dropped: as substrings
    they would match almost any product name.
    """
    return [word for word in _WORD_RE.findall(fold(name_query)) if len(word) >= 3]


def term_variants(term: str) -> tuple[str, ...]:
    """Spanish stems (or the term itself) a query term may match."""
    for key in (term, term.rstrip("s"), term[:-2] if term.endswith("es") else ""):
        if key and key in EN_ES_SYNONYMS:
            return EN_ES_SYNONYMS[key]
    variants = [term]
    if len(term) > 4 and term.endswith("s"):
        variants.append(term[:-1])
    return tuple(variants)


def term_matches(term: str, folded_name: str) -> bool:
    """True when ``term`` (or a synonym / close spelling) appears in the name."""
    variants = term_variants(term)
    if any(variant in folded_name for variant in variants):
        return True
    if len(term) < _FUZZY_MIN_LEN:
        return False
    words = _WORD_RE.findall(folded_name)
    # Typo tolerance on the raw term and on its synonyms, word by word.
    candidates = {term, *variants}
    for candidate in candidates:
        if len(candidate) < _FUZZY_MIN_LEN:
            continue
        if difflib.get_close_matches(candidate, words, n=1, cutoff=_FUZZY_CUTOFF):
            return True
        # English typo -> look up the closest dictionary key ("glovse").
        close_keys = difflib.get_close_matches(
            candidate, list(EN_ES_SYNONYMS), n=1, cutoff=_FUZZY_CUTOFF
        )
        if close_keys and any(
            stem in folded_name for stem in EN_ES_SYNONYMS[close_keys[0]]
        ):
            return True
    return False


class _Named(Protocol):
    name: str


T = TypeVar("T", bound=_Named)


def score_product(terms: Sequence[str], name: str) -> int | None:
    """Ranking score for one product, or ``None`` when it does not match."""
    if not terms:
        return None
    folded = fold(name)
    core = [term for term in terms if term not in SOFT_TERMS]
    soft = [term for term in terms if term in SOFT_TERMS]
    if core:
        if not all(term_matches(term, folded) for term in core):
            return None
        return len(core) * 10 + sum(term_matches(term, folded) for term in soft)
    matched_soft = sum(term_matches(term, folded) for term in soft)
    return matched_soft if matched_soft else None


def filter_products(products: Iterable[T], name_query: str) -> list[T]:
    """Products whose name matches ``name_query``, best match first."""
    terms = query_terms(name_query)
    scored: list[tuple[int, int, T]] = []
    for index, item in enumerate(products):
        score = score_product(terms, item.name)
        if score is not None:
            scored.append((score, index, item))
    if not scored:
        return []
    best = max(score for score, _, _ in scored)
    # Keep only the best-ranked tier: "surgical masks" should not also list
    # every other product that merely shares a soft word.
    return [item for score, _, item in sorted(scored, key=lambda row: row[1]) if score == best]
