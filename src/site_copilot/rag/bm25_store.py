from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi

from site_copilot.rag.store import Chunk, RetrievedChunk

_TOKEN = re.compile(r"[A-Za-z0-9_\-./]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


class BM25Store:
    """In-memory BM25 store. Zero external dependencies, fast for the
    demo's corpus size. Same interface as a production OpenSearch index."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._tokens: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def index(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)
        self._tokens.extend(_tokenize(c.text) for c in chunks)
        if self._tokens:
            self._bm25 = BM25Okapi(self._tokens)

    def search(
        self, query: str, k: int = 6, filters: dict[str, Any] | None = None
    ) -> list[RetrievedChunk]:
        if not self._bm25 or not self._chunks:
            return []

        q_tokens = _tokenize(query)
        scores = self._bm25.get_scores(q_tokens)

        # Apply filters first.
        candidates: list[tuple[int, float]] = []
        q_set = set(q_tokens)
        for idx, (chunk, score) in enumerate(zip(self._chunks, scores, strict=True)):
            if filters:
                ok = True
                for fk, fv in filters.items():
                    if fk == "source_type" and chunk.source_type != fv:
                        ok = False
                        break
                    if fk == "source_id" and chunk.source_id != fv:
                        ok = False
                        break
                if not ok:
                    continue
            candidates.append((idx, float(score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:k]
        results: list[RetrievedChunk] = []
        for idx, score in top:
            if score <= 0:
                continue
            matched = sorted(q_set & set(self._tokens[idx]))[:8]
            results.append(RetrievedChunk(chunk=self._chunks[idx], score=score, matched_terms=matched))
        return results

    def size(self) -> int:
        return len(self._chunks)
