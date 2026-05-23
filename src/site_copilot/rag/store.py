from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Chunk:
    """A retrievable unit. Fields are chosen to mirror an OpenSearch document
    with a kNN dense vector field — swap our BM25Store for OpenSearch and the
    contract holds."""

    chunk_id: str
    source_type: str  # spec | prior_rfi | daily_report
    source_id: str
    section: str | None
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    matched_terms: list[str] = field(default_factory=list)


class VectorStore(Protocol):
    """Minimal store interface. Implementations: BM25Store (default),
    ChromaStore (optional, dense vectors), OpenSearchStore (prod target)."""

    def index(self, chunks: list[Chunk]) -> None: ...

    def search(self, query: str, k: int = 6, filters: dict[str, Any] | None = None) -> list[RetrievedChunk]: ...

    def size(self) -> int: ...
