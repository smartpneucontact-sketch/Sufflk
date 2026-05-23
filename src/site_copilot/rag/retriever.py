from __future__ import annotations

from collections import defaultdict
from typing import Any

from site_copilot.rag.bm25_store import BM25Store
from site_copilot.rag.store import Chunk, RetrievedChunk, VectorStore


class Retriever:
    """Hybrid retriever.

    - mode='bm25': lexical only (default, zero-friction install)
    - mode='hybrid': BM25 + Chroma dense, fused with Reciprocal Rank Fusion.

    Reciprocal Rank Fusion is the standard hybrid-fuse algorithm for
    OpenSearch hybrid search — same math, swap stores for prod."""

    def __init__(self, mode: str = "bm25"):
        self.mode = mode
        self.bm25: VectorStore = BM25Store()
        self.dense: VectorStore | None = None
        if mode == "hybrid":
            from site_copilot.rag.chroma_store import ChromaStore

            self.dense = ChromaStore()

    def index(self, chunks: list[Chunk]) -> None:
        self.bm25.index(chunks)
        if self.dense is not None:
            self.dense.index(chunks)

    def search(
        self, query: str, k: int = 6, filters: dict[str, Any] | None = None
    ) -> list[RetrievedChunk]:
        if self.dense is None:
            return self.bm25.search(query, k=k, filters=filters)
        lex = self.bm25.search(query, k=k * 2, filters=filters)
        dense = self.dense.search(query, k=k * 2, filters=filters)
        return self._rrf(lex, dense, k=k)

    def size(self) -> int:
        return self.bm25.size()

    @staticmethod
    def _rrf(
        a: list[RetrievedChunk], b: list[RetrievedChunk], k: int, c: int = 60
    ) -> list[RetrievedChunk]:
        scores: dict[str, float] = defaultdict(float)
        keep: dict[str, RetrievedChunk] = {}
        for rank, r in enumerate(a):
            scores[r.chunk.chunk_id] += 1.0 / (c + rank)
            keep.setdefault(r.chunk.chunk_id, r)
        for rank, r in enumerate(b):
            scores[r.chunk.chunk_id] += 1.0 / (c + rank)
            keep.setdefault(r.chunk.chunk_id, r)
        ranked = sorted(keep.values(), key=lambda x: scores[x.chunk.chunk_id], reverse=True)
        # Re-score the survivors so callers see the fused score, not the lexical one.
        out: list[RetrievedChunk] = []
        for r in ranked[:k]:
            out.append(RetrievedChunk(chunk=r.chunk, score=scores[r.chunk.chunk_id], matched_terms=r.matched_terms))
        return out
