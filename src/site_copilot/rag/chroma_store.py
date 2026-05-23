"""Dense-vector store backed by Chroma. Optional — only imported when
SITE_COPILOT_RETRIEVER=hybrid. Install with `pip install site-copilot[dense]`.

Production target is OpenSearch kNN — this class proves the contract works
with a real dense store locally."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from site_copilot.rag.store import Chunk, RetrievedChunk


class ChromaStore:
    def __init__(self, persist_dir: Path = Path(".chroma"), collection: str = "site_copilot"):
        try:
            import chromadb
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "chromadb not installed. Install with: pip install -e .[dense]"
            ) from e

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._coll = self._client.get_or_create_collection(collection)
        self._chunks_by_id: dict[str, Chunk] = {}

    def index(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metas = [
            {"source_type": c.source_type, "source_id": c.source_id, "section": c.section or ""}
            for c in chunks
        ]
        self._coll.upsert(ids=ids, documents=docs, metadatas=metas)
        for c in chunks:
            self._chunks_by_id[c.chunk_id] = c

    def search(
        self, query: str, k: int = 6, filters: dict[str, Any] | None = None
    ) -> list[RetrievedChunk]:
        where = None
        if filters:
            where = {k: {"$eq": v} for k, v in filters.items()}

        res = self._coll.query(query_texts=[query], n_results=k, where=where)
        results: list[RetrievedChunk] = []
        if not res or not res.get("ids"):
            return results
        for chunk_id, dist in zip(res["ids"][0], res["distances"][0], strict=True):
            chunk = self._chunks_by_id.get(chunk_id)
            if not chunk:
                continue
            # Convert cosine distance to a similarity-like score in [0, 1].
            score = max(0.0, 1.0 - float(dist))
            results.append(RetrievedChunk(chunk=chunk, score=score))
        return results

    def size(self) -> int:
        return self._coll.count()
