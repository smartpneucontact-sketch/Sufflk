from pathlib import Path

from site_copilot.rag.ingest import load_chunks
from site_copilot.rag.retriever import Retriever


def test_corpus_loads_and_indexes() -> None:
    chunks = load_chunks(Path("data/corpus"))
    assert len(chunks) >= 10, "corpus should have at least 10 chunks"
    types = {c.source_type for c in chunks}
    assert {"spec", "prior_rfi", "daily_report"}.issubset(types)


def test_bm25_retrieves_spec_for_cover_query() -> None:
    chunks = load_chunks(Path("data/corpus"))
    r = Retriever(mode="bm25")
    r.index(chunks)
    results = r.search("interior column cover reinforcing minimum", k=4)
    assert len(results) >= 1
    top = results[0]
    assert top.chunk.source_type == "spec"
    assert "cover" in top.chunk.text.lower()


def test_retriever_filters_by_source_type() -> None:
    chunks = load_chunks(Path("data/corpus"))
    r = Retriever(mode="bm25")
    r.index(chunks)
    results = r.search("high-lift grouting", k=6, filters={"source_type": "prior_rfi"})
    assert all(rc.chunk.source_type == "prior_rfi" for rc in results)
