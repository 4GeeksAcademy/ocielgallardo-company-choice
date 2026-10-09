"""Unit tests for the RAG knowledge base (chunking, retrieval, generation).

All tests run offline: Qdrant, the embedding API, and the generation LLM are
replaced with fakes via ``monkeypatch`` — no live services in CI.

Run:
    python -m pytest tests/pipelines/test_rag.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Make the repo root importable when pytest is invoked from elsewhere.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import data.pipelines.rag as rag_pipeline  # noqa: E402
import data.process.rag as rag_process  # noqa: E402
from data.pipelines.rag import (  # noqa: E402
    INSUFFICIENT_INFO_ANSWER,
    build_prompt,
    generate_answer,
    query,
    retrieve,
)
from data.process.rag import (  # noqa: E402
    SOURCE_DOCUMENTS,
    RagSettings,
    chunk_markdown,
    chunk_point_id,
    embed,
    load_corpus,
)


def _settings(**overrides) -> RagSettings:
    values = {
        "qdrant_url": "http://localhost:6333",
        "collection": "healthcore_knowledge",
        "embedding_api_key": "test-embedding-key",
        "embedding_api_url": "https://openrouter.ai/api/v1",
        "embedding_model": "test-embedding-model",
        "embedding_dim": 8,
        "llm_api_key": "test-llm-key",
        "llm_api_url": "https://api.groq.com/openai/v1",
        "llm_model": "test-generation-model",
    }
    values.update(overrides)
    return RagSettings(**values)


def _payload(text: str, source: str = "appointment-policy") -> dict:
    return {
        "company": "healthcore",
        "source_document": source,
        "section": "Cancellation",
        "language": "en",
        "chunk_index": 0,
        "text": text,
    }


class _FakePoint:
    def __init__(self, score: float, payload: dict) -> None:
        self.score = score
        self.payload = payload


class _FakeQdrant:
    """In-memory stub: returns canned scored points, records the query."""

    def __init__(self, points: list[_FakePoint]) -> None:
        self._points = points
        self.queries: list[dict] = []

    def query_points(self, **kwargs):
        self.queries.append(kwargs)
        return SimpleNamespace(points=self._points[: kwargs["limit"]])

    def close(self) -> None:
        pass


class _FakeOpenAI:
    """Stub for ``openai.OpenAI`` covering embeddings and chat completions."""

    embedding_vector = [0.1] * 8
    completion_text = "Model words"
    last_embedding_model: str | None = None
    last_chat_model: str | None = None

    def __init__(self, *args, **kwargs) -> None:
        pass

    @property
    def embeddings(self):
        class _Embeddings:
            @staticmethod
            def create(model, input):
                _FakeOpenAI.last_embedding_model = model
                texts = input if isinstance(input, list) else [input]
                return SimpleNamespace(
                    data=[
                        SimpleNamespace(embedding=list(_FakeOpenAI.embedding_vector))
                        for _ in texts
                    ]
                )

        return _Embeddings()

    @property
    def chat(self):
        class _Chat:
            @property
            def completions(self):
                return self

            @staticmethod
            def create(**kwargs):
                _FakeOpenAI.last_chat_model = kwargs.get("model")
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content=_FakeOpenAI.completion_text
                            )
                        )
                    ]
                )

        return _Chat()


def test_chunk_markdown_produces_payload_schema() -> None:
    text = (
        "# Coverage\n\n## Accepted plans\n\nWe accept plan A.\n\n## Excluded plans\n\nPlan Z is excluded.\n"
    )
    chunks = chunk_markdown(text, source_document="insurance-coverage")
    assert len(chunks) >= 2
    for index, chunk in enumerate(chunks):
        assert chunk["company"] == "healthcore"
        assert chunk["source_document"] == "insurance-coverage"
        assert chunk["language"] == "en"
        assert chunk["chunk_index"] == index
        assert chunk["section"]
        assert chunk["text"]


def test_long_document_yields_at_least_three_chunks() -> None:
    sections = "\n\n".join(
        f"## Section {number}\n\n" + "\n".join(
            f"Paragraph {para} of section {number} with policy details."
            for para in range(6)
        )
        for number in range(4)
    )
    chunks = chunk_markdown(f"# Policy\n\n{sections}", source_document="appointment-policy")
    assert len(chunks) >= 3


def test_chunk_point_id_is_deterministic() -> None:
    first = chunk_point_id("healthcore_knowledge", "appointment-policy", 0)
    assert first == chunk_point_id("healthcore_knowledge", "appointment-policy", 0)
    assert first != chunk_point_id("healthcore_knowledge", "appointment-policy", 1)
    assert first != chunk_point_id("healthcore_knowledge", "referral-process", 0)


def test_chunk_point_id_differs_by_language() -> None:
    en_id = chunk_point_id("healthcore_knowledge", "appointment-policy", 0, "en")
    es_id = chunk_point_id("healthcore_knowledge", "appointment-policy", 0, "es")
    assert en_id != es_id  # no EN/ES overwrite on upsert


def test_load_corpus_missing_dir_lists_expected_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="healthcore-insurance-coverage.en.md"):
        load_corpus(tmp_path / "does-not-exist")


def test_load_corpus_skips_readme_and_unknown_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# readme", encoding="utf-8")
    (tmp_path / "random-notes.md").write_text("# notes\n\nHello.", encoding="utf-8")
    stem = next(iter(SOURCE_DOCUMENTS))
    (tmp_path / f"{stem}.md").write_text(
        "# Doc\n\n## A\n\nFirst paragraph here.\n", encoding="utf-8"
    )
    chunks = load_corpus(tmp_path)
    assert chunks
    assert {chunk["source_document"] for chunk in chunks} == {SOURCE_DOCUMENTS[stem]}


def test_embed_uses_dedicated_model(monkeypatch) -> None:
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    vector = embed("hello", settings=_settings())
    assert vector == [0.1] * 8
    assert _FakeOpenAI.last_embedding_model == "test-embedding-model"


def test_embed_rejects_generation_model_reuse() -> None:
    settings = _settings(embedding_model="same-model", llm_model="same-model")
    with pytest.raises(ValueError, match="never reuse the generation model"):
        embed("hello", settings=settings)


def test_retrieve_uses_embed_for_the_question(monkeypatch) -> None:
    seen: list[str] = []

    def _spy_embed(text: str, settings=None):
        seen.append(text)
        return [0.1] * 8

    monkeypatch.setattr(rag_pipeline, "embed", _spy_embed)
    fake = _FakeQdrant([_FakePoint(0.9, _payload("relevant chunk"))])
    monkeypatch.setattr(rag_process, "_get_qdrant_client", lambda settings: fake)
    monkeypatch.setattr(
        RagSettings, "from_env", classmethod(lambda cls: _settings())
    )

    chunks = retrieve("my question", k=5, min_score=0.35)

    assert seen == ["my question"]
    assert [chunk["text"] for chunk in chunks] == ["relevant chunk"]


def test_retrieve_excludes_below_min_score(monkeypatch) -> None:
    monkeypatch.setattr(rag_pipeline, "embed", lambda text, settings=None: [0.1] * 8)
    fake = _FakeQdrant(
        [
            _FakePoint(0.9, _payload("relevant chunk")),
            _FakePoint(0.2, _payload("off-topic chunk")),
            _FakePoint(0.5, _payload("borderline chunk")),
        ]
    )
    monkeypatch.setattr(rag_process, "_get_qdrant_client", lambda settings: fake)
    monkeypatch.setattr(
        RagSettings, "from_env", classmethod(lambda cls: _settings())
    )

    chunks = retrieve("question", k=5, min_score=0.35)

    assert [chunk["text"] for chunk in chunks] == ["relevant chunk", "borderline chunk"]


def test_retrieve_returns_payload_dicts_and_may_return_fewer_than_k(
    monkeypatch,
) -> None:
    monkeypatch.setattr(rag_pipeline, "embed", lambda text, settings=None: [0.1] * 8)
    fake = _FakeQdrant(
        [
            _FakePoint(0.9, _payload("first")),
            _FakePoint(0.1, _payload("dropped")),
            _FakePoint(0.8, _payload("second")),
        ]
    )
    monkeypatch.setattr(rag_process, "_get_qdrant_client", lambda settings: fake)
    monkeypatch.setattr(
        RagSettings, "from_env", classmethod(lambda cls: _settings())
    )

    chunks = retrieve("question", k=5, min_score=0.35)

    assert len(chunks) == 2  # fewer than k=5: below-threshold hit excluded
    assert all(isinstance(chunk, dict) for chunk in chunks)
    assert all("text" in chunk and "source_document" in chunk for chunk in chunks)
    assert fake.queries[0]["limit"] == 5


def test_generate_answer_returns_model_output(monkeypatch) -> None:
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    monkeypatch.setattr(
        RagSettings, "from_env", classmethod(lambda cls: _settings())
    )

    answer = generate_answer("question", [_payload("raw database chunk text")])

    assert answer == "Model words"
    assert answer != "raw database chunk text"
    assert _FakeOpenAI.last_chat_model == "test-generation-model"


def test_generate_answer_with_empty_context_still_asks_model(monkeypatch) -> None:
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    monkeypatch.setattr(
        RagSettings, "from_env", classmethod(lambda cls: _settings())
    )

    answer = generate_answer("question", [])

    assert answer == "Model words"  # honesty comes from the model, not a shortcut


def test_generate_answer_falls_back_when_model_returns_nothing(monkeypatch) -> None:
    monkeypatch.setattr("openai.OpenAI", _FakeOpenAI)
    monkeypatch.setattr(
        RagSettings, "from_env", classmethod(lambda cls: _settings())
    )
    _FakeOpenAI.completion_text = ""
    try:
        assert generate_answer("question", [_payload("ctx")]) == INSUFFICIENT_INFO_ANSWER
    finally:
        _FakeOpenAI.completion_text = "Model words"


def test_query_is_retrieve_plus_generate_answer(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def _spy_retrieve(question: str, **kwargs):
        calls["retrieve_question"] = question
        return [_payload("ctx")]

    def _spy_generate(question: str, context: list[dict]):
        calls["generate_question"] = question
        calls["generate_context"] = context
        return "Final string"

    monkeypatch.setattr(rag_pipeline, "retrieve", _spy_retrieve)
    monkeypatch.setattr(rag_pipeline, "generate_answer", _spy_generate)

    assert query("my question") == "Final string"
    assert calls["retrieve_question"] == "my question"
    assert calls["generate_question"] == "my question"
    assert calls["generate_context"] == [_payload("ctx")]


def test_build_prompt_contains_business_rules() -> None:
    prompt = build_prompt("Do you take my insurance?", [_payload("some policy text")])
    assert "some policy text" in prompt
    assert "Medicare" in prompt
    assert "United States" in prompt
    assert "United Kingdom" in prompt
    assert "billing" in prompt


def test_embed_texts_batches_into_single_request(monkeypatch) -> None:
    calls: list[object] = []

    class _BatchEmbeddings:
        def create(self, model, input):
            texts = input if isinstance(input, list) else [input]
            calls.append(list(texts))
            assert model == "test-embedding-model"
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[float(len(t))] * 8) for t in texts]
            )

    class _BatchClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        @property
        def embeddings(self):
            return _BatchEmbeddings()

    monkeypatch.setattr("openai.OpenAI", _BatchClient)

    vectors = rag_process.embed_texts(["aaa", "b", "ccccc"], settings=_settings())

    assert len(calls) == 1  # one POST, not one per text
    assert calls[0] == ["aaa", "b", "ccccc"]  # full array, order preserved
    assert vectors == [[3.0] * 8, [1.0] * 8, [5.0] * 8]
    # Same vectors as singular embed() per text (contract equivalence).
    assert vectors == [embed(t, settings=_settings()) for t in ["aaa", "b", "ccccc"]]


def test_embed_texts_rejects_missing_key() -> None:
    with pytest.raises(RuntimeError, match="EMBEDDING_API_KEY"):
        rag_process.embed_texts(["hello"], settings=_settings(embedding_api_key=""))
