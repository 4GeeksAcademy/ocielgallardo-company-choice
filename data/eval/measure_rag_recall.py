"""Measure Recall@3 for the RAG knowledge base.

For each question in ``test-queries.json``, retrieves the top 3 chunks and
checks whether the expected source document is among them. Target: >= 80%.

Requires an indexed Qdrant collection plus EMBEDDING_* in root .env.

Run:
    uv run python data/eval/measure_rag_recall.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the repo root importable (script lives three levels below it).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data.pipelines.rag import retrieve  # noqa: E402

TARGET_RECALL = 0.8
TOP_K = 3


def main() -> int:
    eval_file = Path(__file__).resolve().parent / "test-queries.json"
    spec = json.loads(eval_file.read_text(encoding="utf-8"))
    queries = spec["queries"]

    hits = 0
    for item in queries:
        chunks = retrieve(item["question"], k=TOP_K)
        sources = {chunk.get("source_document", "") for chunk in chunks}
        expected = item["expected_source_document"]
        ok = expected in sources
        hits += ok
        print(f"[{'HIT' if ok else 'MISS'}] {item['id']}: expected={expected} got={sorted(sources)}")

    recall = hits / len(queries) if queries else 0.0
    print(f"Recall@{TOP_K}: {recall:.2%} ({hits}/{len(queries)}, target {TARGET_RECALL:.0%})")
    return 0 if recall >= TARGET_RECALL else 1


if __name__ == "__main__":
    raise SystemExit(main())
