from __future__ import annotations

import contextvars
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_RUN_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)


def new_run_id() -> str:
    rid = f"run_{uuid.uuid4().hex[:12]}"
    _RUN_ID.set(rid)
    return rid


def current_run_id() -> str | None:
    return _RUN_ID.get()


class Tracer:
    """JSONL tracer.

    One file per day, append-only. Each line is a single event with run_id so
    you can stitch a full agent trace together. Designed to be ingested into
    Databricks or CloudWatch with no transformation — matches the JD's
    'monitor latency, cost, adoption, and drift' line.
    """

    def __init__(self, traces_dir: Path):
        self.traces_dir = traces_dir
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _path(self) -> Path:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.traces_dir / f"traces-{date}.jsonl"

    def event(self, kind: str, **fields: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": current_run_id(),
            "kind": kind,
            **fields,
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def span(self, name: str, **attrs: Any) -> _Span:
        return _Span(self, name, attrs)


class _Span:
    def __init__(self, tracer: Tracer, name: str, attrs: dict[str, Any]):
        self.tracer = tracer
        self.name = name
        self.attrs = attrs
        self.t0 = 0.0

    def __enter__(self) -> _Span:
        self.t0 = time.perf_counter()
        self.tracer.event("span.start", name=self.name, **self.attrs)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (time.perf_counter() - self.t0) * 1000.0
        self.tracer.event(
            "span.end",
            name=self.name,
            elapsed_ms=round(elapsed_ms, 2),
            error=str(exc) if exc else None,
            **self.attrs,
        )
