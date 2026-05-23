"""Walk the synthetic corpus and produce a list of Chunks.

Layout assumed:
    {corpus_dir}/specs/*.md
    {corpus_dir}/prior_rfis/*.md
    {corpus_dir}/daily_reports/*.md

Spec files are chunked by markdown ## heading (each section is one chunk).
RFIs and daily reports are single chunks each — they're small and you almost
always want the whole document together."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from site_copilot.config import get_settings
from site_copilot.rag.retriever import Retriever
from site_copilot.rag.store import Chunk

_SECTION_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _chunk_spec(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    source_id = path.stem
    matches = list(_SECTION_HEADING.finditer(text))
    if not matches:
        return [
            Chunk(
                chunk_id=f"spec:{source_id}",
                source_type="spec",
                source_id=source_id,
                section=None,
                text=text.strip(),
            )
        ]
    chunks: list[Chunk] = []
    for i, m in enumerate(matches):
        section = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        chunks.append(
            Chunk(
                chunk_id=f"spec:{source_id}:{i:02d}",
                source_type="spec",
                source_id=source_id,
                section=section,
                text=body,
            )
        )
    return chunks


def _chunk_whole(path: Path, source_type: str) -> Chunk:
    return Chunk(
        chunk_id=f"{source_type}:{path.stem}",
        source_type=source_type,
        source_id=path.stem,
        section=None,
        text=path.read_text(encoding="utf-8").strip(),
    )


def load_chunks(corpus_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for p in sorted((corpus_dir / "specs").glob("*.md")):
        chunks.extend(_chunk_spec(p))
    for p in sorted((corpus_dir / "prior_rfis").glob("*.md")):
        chunks.append(_chunk_whole(p, "prior_rfi"))
    for p in sorted((corpus_dir / "daily_reports").glob("*.md")):
        chunks.append(_chunk_whole(p, "daily_report"))
    return chunks


def build_retriever() -> Retriever:
    s = get_settings()
    retriever = Retriever(mode=s.retriever)
    chunks = load_chunks(s.corpus_dir)
    retriever.index(chunks)
    return retriever


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the synthetic construction corpus.")
    parser.add_argument("--query", help="Optional query to test after ingestion.")
    args = parser.parse_args()

    s = get_settings()
    chunks = load_chunks(s.corpus_dir)
    print(f"Loaded {len(chunks)} chunks from {s.corpus_dir}")
    breakdown: dict[str, int] = {}
    for c in chunks:
        breakdown[c.source_type] = breakdown.get(c.source_type, 0) + 1
    for k, v in sorted(breakdown.items()):
        print(f"  {k}: {v}")

    if args.query:
        retriever = Retriever(mode=s.retriever)
        retriever.index(chunks)
        results = retriever.search(args.query, k=s.top_k)
        print(f"\nTop {len(results)} results for: {args.query!r}")
        for i, r in enumerate(results, 1):
            head = r.chunk.section or r.chunk.source_id
            print(f"  {i}. [{r.score:.2f}] {r.chunk.source_type}:{r.chunk.source_id} -- {head}")


if __name__ == "__main__":
    main()
